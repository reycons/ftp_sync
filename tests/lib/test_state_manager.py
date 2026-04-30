"""Unit tests for rey_lib/state_manager.py."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from rey_lib.state_manager import (
    is_new_or_updated,
    load_state,
    record_downloaded,
    save_state,
)
from rey_lib.error_utils import StateError


class TestLoadState:
    """Tests for load_state()."""

    def test_returns_empty_dict_when_no_state_file(self, conn):
        """Fresh run with no existing state file returns an empty dict."""
        result = load_state(conn)
        assert result == {}

    def test_loads_existing_state(self, conn):
        """Existing state file is parsed and returned correctly."""
        state_data = {"/incoming/data.csv": "2026-01-15T10:00:00+00:00"}
        conn.state_file.parent.mkdir(parents=True, exist_ok=True)
        conn.state_file.write_text(json.dumps(state_data), encoding="utf-8")

        result = load_state(conn)

        assert result == state_data

    def test_raises_state_error_on_corrupt_json(self, conn):
        """A corrupt state file raises StateError."""
        conn.state_file.parent.mkdir(parents=True, exist_ok=True)
        conn.state_file.write_text("not valid json", encoding="utf-8")

        with pytest.raises(StateError):
            load_state(conn)


class TestSaveState:
    """Tests for save_state()."""

    def test_writes_state_to_disk(self, conn):
        """State dict is persisted as valid JSON."""
        state = {"/incoming/file.csv": "2026-01-15T10:00:00+00:00"}

        save_state(conn, state)

        written = json.loads(conn.state_file.read_text(encoding="utf-8"))
        assert written == state

    def test_creates_parent_directories(self, conn, tmp_path):
        """Parent directories are created if absent."""
        conn.state_file = tmp_path / "nested" / "deep" / "state.json"

        save_state(conn, {})

        assert conn.state_file.exists()


class TestIsNewOrUpdated:
    """Tests for is_new_or_updated()."""

    def test_new_file_not_in_state(self, utc_dt):
        """File absent from state is always new."""
        assert is_new_or_updated({}, "/incoming/", "new.csv", utc_dt) is True

    def test_unchanged_file_not_new(self, utc_dt):
        """File with the same timestamp as state is not considered new."""
        state = {"/incoming/new.csv": utc_dt.isoformat()}
        assert is_new_or_updated(state, "/incoming/", "new.csv", utc_dt) is False

    def test_updated_file_is_new(self, utc_dt):
        """File with a later timestamp than state is considered updated."""
        older = utc_dt - timedelta(hours=1)
        state = {"/incoming/file.csv": older.isoformat()}
        assert is_new_or_updated(state, "/incoming/", "file.csv", utc_dt) is True

    def test_corrupt_timestamp_treated_as_new(self, utc_dt):
        """A corrupt stored timestamp causes the file to be treated as new."""
        state = {"/incoming/file.csv": "not-a-date"}
        assert is_new_or_updated(state, "/incoming/", "file.csv", utc_dt) is True


class TestRecordDownloaded:
    """Tests for record_downloaded()."""

    def test_adds_new_entry(self, utc_dt):
        """A new file is added to the state dict."""
        state: dict[str, str] = {}
        record_downloaded(state, "/incoming/", "file.csv", utc_dt)
        assert "/incoming/file.csv" in state

    def test_overwrites_existing_entry(self, utc_dt):
        """An existing entry is overwritten with the new timestamp."""
        older = utc_dt - timedelta(days=1)
        state = {"/incoming/file.csv": older.isoformat()}
        record_downloaded(state, "/incoming/", "file.csv", utc_dt)
        stored = datetime.fromisoformat(state["/incoming/file.csv"])
        assert stored == utc_dt
