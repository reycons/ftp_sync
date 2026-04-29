"""All logging configuration and helper functions.

No direct logging setup is permitted outside this module.
Provides log_enter() and log_exit() to maintain call-hierarchy indentation
in log output via ctx.log_depth.
"""

from __future__ import annotations

import logging
import logging.handlers
from datetime import datetime
from pathlib import Path

from lib.ctx import AppContext

__all__ = ["init_logging", "log_enter", "log_exit"]

# Two-space indent per depth level.
_INDENT_UNIT = "  "


def init_logging(ctx: AppContext) -> None:
    """Configure the root logger for the application.

    Behaviour by environment:
    - dev:  DEBUG level, writes to both rotating file and console.
    - prod: INFO level, writes to rotating file only.

    After setup, ctx.log_level is updated to match the active level string.

    Args:
        ctx: Populated AppContext.  ctx.log_level is read and then updated.
    """
    numeric_level = getattr(logging, ctx.log_level, logging.INFO)

    # Ensure the log directory exists before creating handlers.
    ctx.log_dir.mkdir(parents=True, exist_ok=True)

    handlers: list[logging.Handler] = [_build_file_handler(ctx, numeric_level)]

    # Console output in dev only — prod logs are file-only.
    if ctx.env == "dev":
        handlers.append(_build_console_handler(numeric_level))

    logging.basicConfig(level=numeric_level, handlers=handlers, force=True)

    # Write the active level name back to ctx so callers can read it.
    ctx.log_level = logging.getLevelName(numeric_level)


def log_enter(ctx: AppContext, msg: str) -> None:
    """Log an entry message at the current depth, then increment ctx.log_depth.

    Call at the start of a function to produce indented, hierarchical log output.

    Args:
        ctx: AppContext whose log_depth is incremented.
        msg: Short description of the function or operation being entered.
    """
    _get_logger().debug("%s→ %s", _indent(ctx), msg)
    ctx.log_depth += 1


def log_exit(ctx: AppContext, msg: str) -> None:
    """Decrement ctx.log_depth, then log an exit message.

    Call at the end of a function (or in a finally block) to close the indent
    opened by the corresponding log_enter() call.

    Args:
        ctx: AppContext whose log_depth is decremented.
        msg: Short description of the function or operation being exited.
    """
    ctx.log_depth = max(0, ctx.log_depth - 1)
    _get_logger().debug("%s← %s", _indent(ctx), msg)


# ── Private helpers ───────────────────────────────────────────────────────────


def _build_file_handler(ctx: AppContext, level: int) -> logging.handlers.RotatingFileHandler:
    """Create and return a configured rotating file handler.

    Log files are named '<app_name>_<YYYY-MM-DD>.log' and rotate at 10 MB,
    keeping 14 backup files (covering ~2 weeks of daily runs).
    """
    date_stamp = datetime.now().strftime("%Y-%m-%d")
    log_file: Path = ctx.log_dir / f"{ctx.app_name}_{date_stamp}.log"

    handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024,   # 10 MB per file
        backupCount=14,               # 14 rotated files
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(_build_formatter())
    return handler


def _build_console_handler(level: int) -> logging.StreamHandler:
    """Create and return a console (stderr) log handler."""
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(_build_formatter())
    return handler


def _build_formatter() -> logging.Formatter:
    """Return the standard log formatter used by all handlers."""
    return logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s  %(module)-22s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _indent(ctx: AppContext) -> str:
    """Return an indentation string matching the current ctx.log_depth."""
    return _INDENT_UNIT * ctx.log_depth


def _get_logger() -> logging.Logger:
    """Return the module-level logger."""
    return logging.getLogger(__name__)
