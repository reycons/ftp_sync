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

from rey_lib.config.config_utils import build_ctx
from rey_lib.logs.log_utils import setup_logging
from rey_lib.ftp.sync_engine import run_sync

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

    # Inject FTP credentials for each connection from .env.
    # Each connection config declares which env vars to read via
    # ftp.user_env and ftp.password_env — fully self-documenting.
    for conn in connections:
        _inject_connection_secrets(conn)

    # Run sync for every connection sequentially.
    total         = 0
    conn_failed   = 0
    for conn in connections:
        try:
            downloaded = run_sync(ctx, conn)
            total += downloaded
        except FtpSyncError as exc:
            log.error("Sync failed for connection '%s': %s", conn.name, exc)
            conn_failed += 1

    log.info(
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


def _inject_connection_secrets(conn: object) -> None:
    """Resolve FTP credentials from .env and inject into the connection Namespace.

    The config file declares which env vars to read via ftp.user_env and
    ftp.password_env — making each connection fully self-documenting.

    Example config:
        ftp:
          user_env: FTP_USER_CLIENT01
          password_env: FTP_PASSWORD_CLIENT01

    Example .env:
        FTP_USER_CLIENT01=joerey
        FTP_PASSWORD_CLIENT01=secret

    Args:
        conn: Connection Namespace with a .ftp child Namespace containing
              user_env and password_env attribute names.
    """
    user_env     = getattr(conn.ftp, "user_env", "")
    password_env = getattr(conn.ftp, "password_env", "")

    user = os.getenv(user_env, "") if user_env else ""
    password = os.getenv(password_env, "") if password_env else ""

    if not user:
        log.warning(
            "No user found for connection '%s' — expected env var '%s' in .env.",
            conn.name, user_env,
        )
    if not password:
        log.warning(
            "No password found for connection '%s' — expected env var '%s' in .env.",
            conn.name, password_env,
        )

    # Inject directly into the ftp child Namespace.
    object.__setattr__(conn.ftp, "user", user)
    object.__setattr__(conn.ftp, "password", password)


if __name__ == "__main__":
    main()
