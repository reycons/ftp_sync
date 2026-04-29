"""ftp_sync entry point.

Orchestration only: parse CLI arguments, build AppContext, run sync.
No business logic lives here.

Usage:
    python main.py --env dev
    python main.py --env prod
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from lib.sync_engine import run_sync
from lib.config_utils import build_ctx
from lib.error_utils import FtpSyncError
from lib.log_utils import init_logging

# Config files live alongside main.py at the project root.
_CONFIG_DIR = Path(__file__).parent

log = logging.getLogger(__name__)


def main() -> None:
    """Entry point: load config, initialise logging, execute sync."""
    args = _parse_args()

    # Build ctx before logging is initialised — errors go to stderr.
    try:
        ctx = build_ctx(env=args.env, config_dir=_CONFIG_DIR)
    except Exception as exc:  # noqa: BLE001 — bootstrap, logging not yet available
        print(f"FATAL: failed to load config — {exc}", file=sys.stderr)
        sys.exit(1)

    init_logging(ctx)
    log.info("=== ftp_sync starting (env=%s) ===", ctx.env)

    try:
        downloaded = run_sync(ctx)
        log.info("=== ftp_sync finished: %d file(s) downloaded ===", downloaded)
        sys.exit(0)
    except FtpSyncError as exc:
        log.error("=== ftp_sync failed: %s ===", exc)
        sys.exit(1)
    except Exception as exc:
        log.exception("=== ftp_sync encountered an unexpected error: %s ===", exc)
        sys.exit(2)


def _parse_args() -> argparse.Namespace:
    """Parse and return CLI arguments.

    Returns:
        Namespace with attribute 'env' set to 'dev' or 'prod'.
    """
    parser = argparse.ArgumentParser(
        description="Download new or updated files from a configured FTP server."
    )
    parser.add_argument(
        "--env",
        required=True,
        choices=["dev", "prod"],
        help="Runtime environment — controls which config file is loaded.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
