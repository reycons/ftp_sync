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
        log_depth=0,
        log_file="logs/ftp_sync_test.log",
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
            max_retry_sessions=3,
        ),
        sync=Namespace(
            chunk_size=10,
            remote_paths=["/incoming/"],
            local_destination=tmp_path / "downloads",
            state_file=tmp_path / "state.json",
            failed_file=tmp_path / ".failed.json",
            initial_stamp=None,
        ),
        filters=Namespace(
            extensions=[".csv"],
            name_pattern=None,
            max_age_days=None,
        ),
        log_depth=0,
    )


@pytest.fixture()
def utc_dt() -> datetime:
    """Fixed UTC datetime for use in tests."""
    return datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Run logging
# ---------------------------------------------------------------------------

def make_run_log(
    tmp_path,
    *,
    app: str = "ftp_sync",
    run_id: str = "00000000-0000-4000-8000-000000000001",
    run_timestamp: str = "20260822_000000",
    path: str | None = None,
):
    """Build a RunLog writing into ``tmp_path``.

    Run logging is owned by ``RunLog``; a test that writes records takes one
    rather than handing logging a context to read fields off.
    """
    from rey_lib.logs.run_log import RunLog

    return RunLog(
        app=app,
        run_id=run_id,
        run_timestamp=run_timestamp,
        log_dir=None if path else str(tmp_path),
        path=path,
    )


@pytest.fixture()
def run_log(tmp_path):
    """The run log a test writes records through."""
    return make_run_log(tmp_path)
