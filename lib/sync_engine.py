"""Orchestrates the FTP sync: compare, filter, and download new files.

Dependency flow:
    main.py → sync_engine → ftp_client, state_manager → lib/
"""

from __future__ import annotations

import fnmatch
import ftplib
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lib.ftp_client import download_file, ftp_session, list_remote_files
from lib.state_manager import (
    is_new_or_updated,
    load_last_stamp,
    load_state,
    record_downloaded,
    save_last_stamp,
    save_state,
)
from lib.ctx import AppContext
from lib.error_utils import FtpDownloadError
from lib.log_utils import log_enter, log_exit

__all__ = ["run_sync"]

log = logging.getLogger(__name__)


def run_sync(ctx: AppContext) -> int:
    """Execute a complete FTP sync run across all configured remote paths.

    Loads persisted state, opens one FTP session, syncs every remote path,
    then saves state when all paths are complete.

    Args:
        ctx: Fully populated AppContext.

    Returns:
        Total number of files successfully downloaded in this run.
    """
    log_enter(ctx, "run_sync")
    state = load_state(ctx)

    # Resolve the high-water mark: persisted stamp from the last run takes
    # priority; falls back to initial_stamp from config on the very first run.
    last_stamp = load_last_stamp(ctx, state)
    if last_stamp is not None:
        log.info("Download cutoff (high-water mark): %s", last_stamp.isoformat())

    total_downloaded = 0

    with ftp_session(ctx) as ftp:
        for remote_path in ctx.remote_paths:
            count = _sync_path(ctx, ftp, remote_path, state, last_stamp)
            total_downloaded += count

    # Save state once after all paths are processed so a mid-run failure
    # does not leave state partially updated.
    save_last_stamp(ctx, state)
    save_state(ctx, state)

    log.info("Sync complete — total downloaded this run: %d", total_downloaded)
    log_exit(ctx, "run_sync done")
    return total_downloaded


# ── Private helpers ───────────────────────────────────────────────────────────


def _sync_path(
    ctx: AppContext,
    ftp: ftplib.FTP,
    remote_path: str,
    state: dict[str, str],
    last_stamp: datetime | None,
) -> int:
    """Sync a single remote directory.

    Fetches the remote file listing, applies the stamp cutoff, applies config
    filters, identifies new or updated files, then downloads them in chunks.

    Args:
        ctx:         AppContext.
        ftp:         Authenticated FTP connection (shared across all paths).
        remote_path: Remote directory to process.
        state:       Current state dict, mutated in place as files are downloaded.
        last_stamp:  High-water mark from the previous run; files at or before
                     this timestamp are skipped without checking per-file state.

    Returns:
        Number of files downloaded from this path.
    """
    log_enter(ctx, f"_sync_path: {remote_path}")
    log.info("Scanning: %s", remote_path)

    all_files = list_remote_files(ctx, ftp, remote_path)
    log.info("Remote files found: %d", len(all_files))

    # Apply the stamp cutoff first — cheapest filter, no per-file state lookup.
    after_stamp = _filter_by_stamp(all_files, last_stamp)
    log.info("After stamp cutoff: %d", len(after_stamp))

    filtered = _apply_filters(ctx, after_stamp)
    log.info("After config filters: %d", len(filtered))

    # Identify which filtered files are absent from or newer than state.
    to_download = [
        (name, dt)
        for name, dt in filtered
        if is_new_or_updated(state, remote_path, name, dt)
    ]
    log.info("New or updated: %d", len(to_download))

    downloaded = _download_in_chunks(ctx, ftp, remote_path, to_download, state)
    log_exit(ctx, f"_sync_path done: {downloaded} downloaded")
    return downloaded


def _download_in_chunks(
    ctx: AppContext,
    ftp: ftplib.FTP,
    remote_path: str,
    files: list[tuple[str, datetime]],
    state: dict[str, str],
) -> int:
    """Download *files* in groups of ctx.chunk_size, updating state after each success.

    Processing in chunks limits memory usage and ensures state is updated
    progressively even if the run is interrupted.

    Args:
        ctx:         AppContext.
        ftp:         Authenticated FTP connection.
        remote_path: Remote directory the files live in.
        files:       List of (filename, modified_utc) tuples to download.
        state:       State dict mutated in place on each successful download.

    Returns:
        Total number of files successfully downloaded.
    """
    log_enter(ctx, "_download_in_chunks")
    local_dir = _local_dir_for_path(ctx, remote_path)
    downloaded = 0

    for chunk_start in range(0, len(files), ctx.chunk_size):
        chunk = files[chunk_start : chunk_start + ctx.chunk_size]
        chunk_end = min(chunk_start + ctx.chunk_size, len(files))
        log.debug("Processing chunk: files %d–%d of %d", chunk_start + 1, chunk_end, len(files))

        for filename, modified_dt in chunk:
            downloaded += _download_one(
                ctx, ftp, remote_path, filename, modified_dt, local_dir, state
            )

    log_exit(ctx, "_download_in_chunks done")
    return downloaded


def _download_one(
    ctx: AppContext,
    ftp: ftplib.FTP,
    remote_path: str,
    filename: str,
    modified_dt: datetime,
    local_dir: Path,
    state: dict[str, str],
) -> int:
    """Download a single file and record it in state on success.

    A per-file failure is logged but does not abort the run — the function
    returns 0 so the caller can count failures without stopping.

    Args:
        ctx:         AppContext.
        ftp:         Authenticated FTP connection.
        remote_path: Remote directory the file lives in.
        filename:    Basename of the file.
        modified_dt: Modification timestamp (used to update state).
        local_dir:   Local directory to save the file into.
        state:       State dict mutated in place on success.

    Returns:
        1 on success, 0 on failure.
    """
    try:
        download_file(ctx, ftp, remote_path, filename, local_dir)
        record_downloaded(state, remote_path, filename, modified_dt)
        return 1
    except FtpDownloadError as exc:
        log.error("Download failed — %s/%s: %s", remote_path, filename, exc)
        return 0


def _filter_by_stamp(
    files: list[tuple[str, datetime]],
    last_stamp: datetime | None,
) -> list[tuple[str, datetime]]:
    """Discard files whose modification time is at or before the high-water mark.

    This is applied before per-file state checks and config filters because it
    eliminates the bulk of already-seen files in a single pass with no I/O.

    Args:
        files:      Full remote listing as (filename, modified_utc) tuples.
        last_stamp: High-water mark from the previous run; None means no cutoff.

    Returns:
        Files strictly newer than last_stamp, or all files if last_stamp is None.
    """
    if last_stamp is None:
        return files

    result: list[tuple[str, datetime]] = []
    for name, dt in files:
        dt_aware = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        if dt_aware > last_stamp:
            result.append((name, dt))
    return result


def _apply_filters(
    ctx: AppContext,
    files: list[tuple[str, datetime]],
) -> list[tuple[str, datetime]]:
    """Apply all config-driven filters to the file list in order.

    Filters are applied sequentially:
    1. Extension  (ctx.filter_extensions)
    2. Name pattern (ctx.filter_name_pattern)
    3. Max age     (ctx.filter_max_age_days)

    Args:
        ctx:   AppContext carrying filter settings.
        files: Full remote file listing as (filename, modified_utc) tuples.

    Returns:
        Filtered list; original order preserved.
    """
    result = files
    result = _filter_by_extension(ctx, result)
    result = _filter_by_name_pattern(ctx, result)
    result = _filter_by_max_age(ctx, result)
    return result


def _filter_by_extension(
    ctx: AppContext,
    files: list[tuple[str, datetime]],
) -> list[tuple[str, datetime]]:
    """Retain only files whose extension is in ctx.filter_extensions.

    If filter_extensions is empty, all files pass through.
    Comparison is case-insensitive.
    """
    if not ctx.filter_extensions:
        return files
    return [
        (name, dt)
        for name, dt in files
        if Path(name).suffix.lower() in ctx.filter_extensions
    ]


def _filter_by_name_pattern(
    ctx: AppContext,
    files: list[tuple[str, datetime]],
) -> list[tuple[str, datetime]]:
    """Retain only files whose name matches ctx.filter_name_pattern (glob).

    If filter_name_pattern is None, all files pass through.
    Matching is case-insensitive.
    """
    if not ctx.filter_name_pattern:
        return files
    pattern = ctx.filter_name_pattern.lower()
    return [
        (name, dt)
        for name, dt in files
        if fnmatch.fnmatch(name.lower(), pattern)
    ]


def _filter_by_max_age(
    ctx: AppContext,
    files: list[tuple[str, datetime]],
) -> list[tuple[str, datetime]]:
    """Retain only files whose modification time is within ctx.filter_max_age_days.

    If filter_max_age_days is None, all files pass through.
    Naive datetimes are assumed to be UTC.
    """
    if ctx.filter_max_age_days is None:
        return files

    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=ctx.filter_max_age_days)
    result: list[tuple[str, datetime]] = []
    for name, dt in files:
        # Attach UTC timezone to naive timestamps before comparison.
        dt_aware = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        if dt_aware >= cutoff:
            result.append((name, dt))
    return result


def _local_dir_for_path(ctx: AppContext, remote_path: str) -> Path:
    """Map a remote path to a mirrored local subdirectory.

    Strips the leading slash so the path joins correctly on Windows.
    Example: remote '/incoming/reports/' → '<local_destination>/incoming/reports/'
    """
    relative = remote_path.lstrip("/")
    return ctx.local_destination / relative
