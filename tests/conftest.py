"""Shared pytest fixtures for ftp_sync tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from lib.ctx import AppContext


@pytest.fixture()
def ctx(tmp_path: Path) -> AppContext:
    """Return a minimal AppContext wired to a temporary directory."""
    return AppContext(
        env="dev",
        log_level="DEBUG",
        log_depth=0,
        log_dir=tmp_path / "logs",
        app_name="ftp_sync_test",
        chunk_size=10,
        ftp_host="ftp.example.com",
        ftp_port=21,
        ftp_user="user",
        ftp_password="password",
        remote_paths=["/incoming/"],
        local_destination=tmp_path / "downloads",
        state_file=tmp_path / "state.json",
        filter_extensions=[".csv"],
        filter_name_pattern=None,
        filter_max_age_days=None,
        schedule_description="Test only",
    )


@pytest.fixture()
def utc_dt() -> datetime:
    """Return a fixed UTC datetime for use in tests."""
    return datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
