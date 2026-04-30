"""ftp_sync project-specific exceptions."""

from __future__ import annotations
from rey_lib.errors.error_utils import AppError

__all__ = ["FtpSyncError"]


class FtpSyncError(AppError):
    """Base exception for all ftp_sync application errors."""
