"""Context object — all config and runtime state for ftp_sync."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__all__ = ["AppContext"]


@dataclass
class AppContext:
    """Single source of truth for all runtime configuration and state.

    Created once at startup by config_utils.build_ctx() and passed as the
    first argument to every function that requires it.  No attribute may be
    added after startup except log_depth, which changes during execution.
    """

    # ── Environment ──────────────────────────────────────────────────────────
    env: str                    # 'dev' | 'prod'

    # ── Logging ──────────────────────────────────────────────────────────────
    log_level: str              # 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR'
    log_depth: int              # current indentation depth for log readability
    log_dir: Path               # directory where rotating log files are written
    app_name: str               # embedded in log file names

    # ── Data handling ────────────────────────────────────────────────────────
    chunk_size: int             # max files processed per download chunk

    # ── FTP ──────────────────────────────────────────────────────────────────
    ftp_host: str
    ftp_port: int
    ftp_user: str
    ftp_password: str           # resolved from .env — never from YAML

    # ── Sync ─────────────────────────────────────────────────────────────────
    remote_paths: list[str]     # remote directories to watch
    local_destination: Path     # local root directory for all downloads
    state_file: Path            # JSON file that tracks last-seen file timestamps

    # ── Filters ──────────────────────────────────────────────────────────────
    filter_extensions: list[str]       # e.g. ['.csv', '.txt']; empty = all files
    filter_name_pattern: str | None    # glob pattern e.g. 'report_*'; None = no filter
    filter_max_age_days: int | None    # skip files older than N days; None = no limit

    # ── Schedule (documentation — enforced by Windows Task Scheduler) ────────
    schedule_description: str   # human-readable description of the configured schedule
