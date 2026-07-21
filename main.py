"""ftp_sync entry point.

Orchestration only: parse CLI arguments, build context, inject secrets,
run sync for every configured connection.

No business logic lives here.

Usage:
    python main.py --config-path /path/to/configs/v01/config.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Pre-parse --config-path / --config-dir and call load_dotenv before other imports.
from rey_lib.config.cli import preparse_config_args
preparse_config_args()

from rey_lib.config.cli import add_config_args, apply_env_overrides, build_ctx_from_args
from rey_lib.ftp.sync_engine import run_sync
from rey_lib.logs import get_logger, setup_logging

from ftp_sync.error_utils import FtpSyncError

# Project root is the directory containing this file.
_PROJECT_ROOT = Path(__file__).parent
APP_NAME = "ftp_sync"


def main() -> None:
    """Entry point: load config, inject secrets, run sync for every connection."""
    args = _parse_args()
    apply_env_overrides(args.env_overrides)

    # Build ctx — loads all YAML files under config/, resolves paths.
    try:
        if not args.config_path:
            raise SystemExit("--config-path is required.")
        ctx = build_ctx_from_args(args, app_name=APP_NAME)

    except Exception as exc:  # noqa: BLE001 — logging not yet initialised
        print(f"FATAL: failed to load config — {exc}", file=sys.stderr)
        sys.exit(1)

    # Initialise logging — one log file per run, named with timestamp.
    setup_logging(ctx, operation="sync")
    _logger = get_logger(__name__)
    _logger.info("=== ftp_sync starting ===")

    # The connections registry is shared: it may hold database connections
    # (provider block) alongside FTP jobs. Process only entries that define an
    # ftp configuration block.
    all_connections = getattr(ctx, "connections", [])
    connections = [c for c in all_connections if getattr(c, "ftp", None) is not None]

    skipped = len(all_connections) - len(connections)
    if skipped:
        _logger.info("Skipping %d non-FTP connection(s) with no ftp block.", skipped)

    if not connections:
        _logger.error("No FTP connections defined in config — nothing to do.")
        sys.exit(1)

    # FTP credentials are resolved by build_ctx via env.<name> references.
    # Validate and warn when required values are missing.
    for conn in connections:
        _validate_connection_secrets(conn, _logger)

    # Run sync for every connection sequentially.
    total         = 0
    conn_failed   = 0
    for conn in connections:
        try:
            downloaded = run_sync(ctx, conn, resync=args.resync)
            total += downloaded
        except FtpSyncError as exc:
            _logger.error("Sync failed for connection '%s': %s", conn.name, exc)
            conn_failed += 1

    _logger.info(
        "=== ftp_sync finished — total downloaded: %d, failed connections: %d ===",
        total, conn_failed,
    )
    # Exit non-zero if any connection failed entirely — individual file failures
    # are queued for retry and do not affect the exit code here.
    sys.exit(0 if conn_failed == 0 else 1)


def _parse_args() -> argparse.Namespace:
    """Parse and return CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Download new or updated files from all configured FTP connections."
    )
    add_config_args(parser)
    resync_group = parser.add_mutually_exclusive_group()
    resync_group.add_argument(
        "--resync",
        dest="resync",
        action="store_true",
        default=True,
        help="Check every remote file against state (default).",
    )
    resync_group.add_argument(
        "--no-resync",
        dest="resync",
        action="store_false",
        help=(
            "Use the high-water mark stamp to skip files older than the last run. "
            "Faster for routine runs on large remote directories."
        ),
    )
    return parser.parse_args()


def _validate_connection_secrets(conn: object, _logger: object) -> None:
    """Warn if resolved FTP user/password are missing for a connection."""
    user = getattr(conn.ftp, "user", "")
    password = getattr(conn.ftp, "password", "")

    if not user:
        _logger.warning("No FTP user resolved for connection '%s'.", conn.name)
    if not password:
        _logger.warning("No FTP password resolved for connection '%s'.", conn.name)


if __name__ == "__main__":
    main()
