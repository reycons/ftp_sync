"""ftp_sync entry point.

Orchestration only: parse CLI arguments, build context, inject secrets,
run sync for every configured connection.

No business logic lives here.

Usage:
    python main.py --env dev
    python main.py --env prod
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from rey_lib.config.config_utils import build_ctx
from rey_lib.ftp.sync_engine import run_sync
from rey_lib.logs.log_utils import get_logger, setup_logging

from ftp_sync.error_utils import FtpSyncError

# Project root is the directory containing this file.
_PROJECT_ROOT = Path(__file__).parent


def main() -> None:
    """Entry point: load config, inject secrets, run sync for every connection."""
    args = _parse_args()

    # Build ctx — loads all YAML files under config/, resolves paths.
    try:
        load_dotenv(_PROJECT_ROOT / ".env")
        config_dir = os.getenv("APP_CONFIG_DIR")

        ctx = build_ctx(
            env=args.env,
            project_root=PROJECT_ROOT,
            config_dir=config_dir,
        )

    except Exception as exc:  # noqa: BLE001 — logging not yet initialised
        print(f"FATAL: failed to load config — {exc}", file=sys.stderr)
        sys.exit(1)

    # Initialise logging — one log file per run, named with timestamp.
    setup_logging(ctx, operation="sync")
    _logger = get_logger(__name__)
    _logger.info("=== ftp_sync starting (env=%s) ===", ctx.env)

    # Connections are defined in config/data_feeds/ftp.{name}.yaml files.
    connections = getattr(ctx, "connections", [])
    if not connections:
        _logger.error("No connections defined in config — nothing to do.")
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
            downloaded = run_sync(ctx, conn)
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
    parser.add_argument(
        "--env",
        required=True,
        choices=["dev", "prod"],
        help="Runtime environment — controls which config file is loaded.",
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
