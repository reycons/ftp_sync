"""Shared pytest fixtures for ftp_sync tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from argparse import Namespace
from rey_lib.config_utils import build_ctx


@pytest.fixture()
def ctx(tmp_path: Path) -> Namespace:
	ctx = build_ctx("dev")
	ctx.state_file = tmp_path / "state.json"
	return ctx


@pytest.fixture()
def utc_dt() -> datetime:
	return datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
