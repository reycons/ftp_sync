"""Unit tests for rey_lib/sync_engine.py — filter functions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from rey_lib.sync_engine import (
    _apply_filters,
    _filter_by_extension,
    _filter_by_max_age,
    _filter_by_name_pattern,
)

_NOW = datetime.now(tz=timezone.utc)


def _file(name: str, days_old: int = 0) -> tuple[str, datetime]:
    """Helper — build a (filename, modified_utc) tuple."""
    return (name, _NOW - timedelta(days=days_old))


class TestFilterByExtension:
    """Tests for _filter_by_extension()."""

    def test_passes_matching_extension(self, conn):
        conn.filters.extensions = [".csv"]
        files = [_file("a.csv"), _file("b.txt")]
        assert _filter_by_extension(conn, files) == [_file("a.csv")]

    def test_empty_extension_list_passes_all(self, conn):
        conn.filters.extensions = []
        files = [_file("a.csv"), _file("b.txt")]
        assert _filter_by_extension(conn, files) == files

    def test_case_insensitive(self, conn):
        conn.filters.extensions = [".csv"]
        files = [_file("DATA.CSV")]
        assert len(_filter_by_extension(conn, files)) == 1


class TestFilterByNamePattern:
    """Tests for _filter_by_name_pattern()."""

    def test_passes_matching_pattern(self, conn):
        conn.filters.name_pattern = "report_*"
        files = [_file("report_jan.csv"), _file("summary.csv")]
        result = _filter_by_name_pattern(conn, files)
        assert len(result) == 1
        assert result[0][0] == "report_jan.csv"

    def test_none_pattern_passes_all(self, conn):
        conn.filters.name_pattern = None
        files = [_file("a.csv"), _file("b.csv")]
        assert _filter_by_name_pattern(conn, files) == files


class TestFilterByMaxAge:
    """Tests for _filter_by_max_age()."""

    def test_passes_recent_file(self, conn):
        conn.filters.max_age_days = 7
        files = [_file("recent.csv", days_old=3)]
        assert len(_filter_by_max_age(conn, files)) == 1

    def test_excludes_old_file(self, conn):
        conn.filters.max_age_days = 7
        files = [_file("old.csv", days_old=10)]
        assert len(_filter_by_max_age(conn, files)) == 0

    def test_none_max_age_passes_all(self, conn):
        conn.filters.max_age_days = None
        files = [_file("ancient.csv", days_old=3650)]
        assert _filter_by_max_age(conn, files) == files


class TestApplyFilters:
    """Integration test — all filters applied in sequence."""

    def test_all_filters_combined(self, conn):
        conn.filters.extensions   = [".csv"]
        conn.filters.name_pattern = "report_*"
        conn.filters.max_age_days = 7

        files = [
            _file("report_jan.csv", days_old=2),   # passes all
            _file("report_old.csv", days_old=30),  # fails max_age
            _file("summary.csv",    days_old=1),   # fails pattern
            _file("report_jan.txt", days_old=1),   # fails extension
        ]
        result = _apply_filters(conn, files)
        assert len(result) == 1
        assert result[0][0] == "report_jan.csv"
