"""ftp_sync project-specific exceptions.

All exceptions extend AppError from rey_lib so callers can catch at
either the project level or the library base level.

No broad except blocks are permitted outside this module.
"""

from __future__ import annotations

from rey_lib.errors.error_utils import AppError

__all__ = [
    "FtpSyncError",
]


class FtpSyncError(AppError):
    """Base exception for all ftp_sync application errors."""
