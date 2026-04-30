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
import logging
import os
import sys
from pathlib import Path

from rey_lib.config_utils import build_ctx
from rey_lib.log_utils import setup_logging
from rey_lib.sync_engine import run_sync

from app.error_utils import FtpSyncError

# Project root is the directory containing this file.
_PROJECT_ROOT = Path(__file__).parent

log = logging.getLogger(__name__)


def main() -> None:
    """Entry point: load config, inject secrets, run sync for every connection."""
    args = _parse_args()

    # Build ctx — loads all YAML files under config/, resolves paths.
    try:
        ctx = build_ctx(env=args.env, project_root=_PROJECT_ROOT)
    except Exception as exc:  # noqa: BLE001 — logging not yet initialised
        print(f"FATAL: failed to load config — {exc}", file=sys.stderr)
        sys.exit(1)

    # Initialise logging — one log file per run, named with timestamp.
    setup_logging(ctx, operation="sync")
    log.info("=== ftp_sync starting (env=%s) ===", ctx.env)

    # Connections are defined in config/ftp.{name}.yaml files.
    connections = getattr(ctx, "connections", [])
    if not connections:
        log.error("No connections defined in config — nothing to do.")
        sys.exit(1)

    # Inject FTP password for each connection from .env.
    # Convention: FTP_PASSWORD_{NAME_UPPER} e.g. FTP_PASSWORD_CLIENTA
    for conn in connections:
        _inject_connection_password(conn)

    # Run sync for every connection sequentially.
    total  = 0
    failed = 0
    for conn in connections:
        try:
            downloaded = run_sync(ctx, conn)
            total += downloaded
        except FtpSyncError as exc:
            log.error("Sync failed for connection '%s': %s", conn.name, exc)
            failed += 1

    log.info(
        "=== ftp_sync finished — total downloaded: %d, failed connections: %d ===",
        total, failed,
    )
    sys.exit(0 if failed == 0 else 1)


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


def _inject_connection_password(conn: object) -> None:
    """Resolve FTP password from .env and inject into the connection Namespace.

    Convention: env var name is FTP_PASSWORD_{CONNECTION_NAME_UPPER}.
    Example: connection name 'clienta' → env var 'FTP_PASSWORD_CLIENTA'.

    Args:
        conn: Connection Namespace with a .name attribute and a .ftp child Namespace.
    """
    env_var  = f"FTP_PASSWORD_{conn.name.upper()}"
    password = os.getenv(env_var, "")
    if not password:
        log.warning(
            "No password found for connection '%s' — expected env var '%s' in .env.",
            conn.name, env_var,
        )
    # Inject directly into the ftp child Namespace.
    object.__setattr__(conn.ftp, "password", password)


if __name__ == "__main__":
    main()
