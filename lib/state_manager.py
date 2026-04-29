"""Tracks which FTP files have already been downloaded using a JSON state file.

State format:
    { "<remote_path>/<filename>": "<ISO-8601 UTC timestamp>", ... }

A file is considered new if its key is absent from state.
A file is considered updated if its remote modification time is later than stored.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from lib.ctx import AppContext
from lib.error_utils import StateError
from lib.log_utils import log_enter, log_exit

__all__ = ["load_state", "save_state", "is_new_or_updated", "record_downloaded"]

log = logging.getLogger(__name__)


def load_state(ctx: AppContext) -> dict[str, str]:
    """Load the download state from the JSON state file.

    Returns an empty dict if the file does not yet exist — this is the
    expected condition on the very first run.

    Args:
        ctx: AppContext carrying the state_file path.

    Returns:
        Dict mapping '<remote_path>/<filename>' → ISO-8601 UTC timestamp string.

    Raises:
        StateError: If the file exists but cannot be read or parsed.
    """
    log_enter(ctx, "load_state")
    state_file: Path = ctx.state_file

    if not state_file.exists():
        log.info("No state file at '%s' — starting fresh.", state_file)
        log_exit(ctx, "load_state done (fresh)")
        return {}

    try:
        with state_file.open(encoding="utf-8") as f:
            state: dict[str, str] = json.load(f)
        log.info("Loaded state: %d entry/entries from '%s'", len(state), state_file)
        log_exit(ctx, "load_state done")
        return state
    except (OSError, json.JSONDecodeError) as exc:
        raise StateError(f"Cannot read state file '{state_file}'.") from exc


def save_state(ctx: AppContext, state: dict[str, str]) -> None:
    """Persist the download state to the JSON state file.

    Creates parent directories if they do not exist.  Keys are written in
    sorted order to produce stable, diff-friendly output.

    Args:
        ctx:   AppContext carrying the state_file path.
        state: Current state dict to persist.

    Raises:
        StateError: If the file cannot be written.
    """
    log_enter(ctx, "save_state")
    state_file: Path = ctx.state_file
    state_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        with state_file.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=True)
        log.info("Saved state: %d entry/entries to '%s'", len(state), state_file)
    except OSError as exc:
        raise StateError(f"Cannot write state file '{state_file}'.") from exc
    finally:
        log_exit(ctx, "save_state done")


def is_new_or_updated(
    state: dict[str, str],
    remote_path: str,
    filename: str,
    modified_dt: datetime,
) -> bool:
    """Return True if the file is absent from state or has a newer modification time.

    Args:
        state:       Current state dict.
        remote_path: Remote directory the file lives in.
        filename:    Basename of the file.
        modified_dt: Modification timestamp reported by the FTP server.

    Returns:
        True  — file should be downloaded.
        False — file is already current in state.
    """
    key = _state_key(remote_path, filename)

    # File has never been downloaded.
    if key not in state:
        return True

    # Parse the stored timestamp; if it is corrupt, treat the file as new.
    try:
        last_seen_dt = datetime.fromisoformat(state[key])
    except ValueError:
        return True

    # Ensure both timestamps are timezone-aware before comparing.
    modified_dt = _ensure_utc(modified_dt)
    last_seen_dt = _ensure_utc(last_seen_dt)

    return modified_dt > last_seen_dt


def record_downloaded(
    state: dict[str, str],
    remote_path: str,
    filename: str,
    modified_dt: datetime,
) -> None:
    """Record that a file was successfully downloaded by updating state in place.

    Args:
        state:       State dict to update (mutated in place).
        remote_path: Remote directory the file lives in.
        filename:    Basename of the file.
        modified_dt: Modification timestamp to record.
    """
    key = _state_key(remote_path, filename)
    state[key] = _ensure_utc(modified_dt).isoformat()


# ── Private helpers ───────────────────────────────────────────────────────────


def _state_key(remote_path: str, filename: str) -> str:
    """Build the canonical state dict key for a remote file.

    Example: remote_path='/incoming/', filename='data.csv' → '/incoming/data.csv'
    """
    return f"{remote_path.rstrip('/')}/{filename}"


def _ensure_utc(dt: datetime) -> datetime:
    """Return *dt* with UTC timezone attached if it is naive."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
