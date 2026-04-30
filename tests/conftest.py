"""Shared pytest fixtures for ftp_sync tests."""

from __future__ import annotations

from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

import pytest


@pytest.fixture()
def ctx() -> Namespace:
    """Minimal global context Namespace for tests."""
    return Namespace(
        env="dev",
        log_depth=0,
        sync=Namespace(chunk_size=10),
    )


@pytest.fixture()
def conn(tmp_path: Path) -> Namespace:
    """Minimal per-connection Namespace wired to a temporary directory."""
    return Namespace(
        name="testconn",
        ftp=Namespace(
            host="ftp.example.com",
            port=21,
            user="user",
            password="password",
        ),
        sync=Namespace(
            remote_paths=["/incoming/"],
            local_destination=tmp_path / "downloads",
            state_file=tmp_path / "state.json",
            initial_stamp=None,
        ),
        filters=Namespace(
            extensions=[".csv"],
            name_pattern=None,
            max_age_days=None,
        ),
        # Convenience aliases used directly by state_manager functions.
        state_file=tmp_path / "state.json",
        initial_stamp=None,
        log_depth=0,
    )


@pytest.fixture()
def utc_dt() -> datetime:
    """Fixed UTC datetime for use in tests."""
    return datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
