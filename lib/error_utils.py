"""Centralised error handling, exception formatting, and custom exceptions.

All custom exception classes are defined here.
All broad exception catching (except Exception) is confined to this module.
No bare except blocks are permitted elsewhere in the project.
"""

from __future__ import annotations

import logging
import traceback
from typing import NoReturn

__all__ = [
    "FtpSyncError",
    "ConfigError",
    "FtpConnectionError",
    "FtpDownloadError",
    "StateError",
    "handle_fatal",
    "validate_not_none",
    "validate_type",
]

log = logging.getLogger(__name__)


# ── Custom exception hierarchy ────────────────────────────────────────────────


class FtpSyncError(Exception):
    """Base exception for all ftp_sync errors."""


class ConfigError(FtpSyncError):
    """Raised when configuration is missing, invalid, or incompatible."""


class FtpConnectionError(FtpSyncError):
    """Raised when an FTP connection cannot be established or is unexpectedly lost."""


class FtpDownloadError(FtpSyncError):
    """Raised when a file download fails or is incomplete."""


class StateError(FtpSyncError):
    """Raised when the state file cannot be read, parsed, or written."""


# ── Error handling helpers ────────────────────────────────────────────────────


def handle_fatal(exc: Exception, context_msg: str) -> NoReturn:
    """Log a fatal exception with full traceback and re-raise as FtpSyncError.

    This is the single exit point for unrecoverable errors encountered
    outside the normal module-level handlers.

    Args:
        exc:         The original exception.
        context_msg: Human-readable description of what was happening.

    Raises:
        FtpSyncError: Always raised, wrapping the original exception.
    """
    log.error("%s: %s", context_msg, exc)
    log.debug("Full traceback:\n%s", traceback.format_exc())
    raise FtpSyncError(context_msg) from exc


def validate_not_none(value: object, name: str) -> None:
    """Assert that a config or input value is not None.

    Args:
        value: The value to check.
        name:  Descriptive name used in the error message.

    Raises:
        ConfigError: If value is None.
    """
    if value is None:
        raise ConfigError(f"Required value '{name}' is missing (None).")


def validate_type(value: object, name: str, expected_type: type) -> None:
    """Assert that a value is an instance of the expected type.

    Args:
        value:         The value to check.
        name:          Descriptive name used in the error message.
        expected_type: The type the value must be an instance of.

    Raises:
        ConfigError: If value is not an instance of expected_type.
    """
    if not isinstance(value, expected_type):
        raise ConfigError(
            f"Value '{name}' must be {expected_type.__name__}, "
            f"got {type(value).__name__}."
        )
