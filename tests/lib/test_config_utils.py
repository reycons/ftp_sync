"""Unit tests for lib/config_utils.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from lib.config_utils import _normalise_extensions, _resolve_log_level, build_ctx


class TestNormaliseExtensions:
    """Tests for _normalise_extensions()."""

    def test_adds_missing_dot(self):
        assert _normalise_extensions(["csv"]) == [".csv"]

    def test_preserves_existing_dot(self):
        assert _normalise_extensions([".csv"]) == [".csv"]

    def test_lowercases_extension(self):
        assert _normalise_extensions([".CSV"]) == [".csv"]

    def test_empty_list_returns_empty(self):
        assert _normalise_extensions([]) == []

    def test_strips_whitespace(self):
        assert _normalise_extensions(["  .CSV  "]) == [".csv"]


class TestResolveLogLevel:
    """Tests for _resolve_log_level()."""

    def test_explicit_config_value_wins(self):
        config = {"logging": {"level": "WARNING"}}
        assert _resolve_log_level("dev", config) == "WARNING"

    def test_defaults_to_debug_in_dev(self):
        assert _resolve_log_level("dev", {}) == "DEBUG"

    def test_defaults_to_info_in_prod(self):
        assert _resolve_log_level("prod", {}) == "INFO"


class TestBuildCtx:
    """Tests for build_ctx()."""

    def test_raises_when_config_file_missing(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            build_ctx(env="dev", config_dir=tmp_path)

    def test_raises_when_ftp_password_env_not_set(self, tmp_path: Path, monkeypatch):
        """Missing FTP_PASSWORD in environment raises EnvironmentError."""
        monkeypatch.delenv("FTP_PASSWORD", raising=False)
        config_content = """
logging:
  level: DEBUG
  log_dir: logs
  app_name: ftp_sync
ftp:
  host: ftp.example.com
  port: 21
  user: user
sync:
  remote_paths: [/incoming/]
  local_destination: C:/downloads
  state_file: state.json
  chunk_size: 10
"""
        (tmp_path / "config.dev.yaml").write_text(config_content, encoding="utf-8")
        with pytest.raises(EnvironmentError, match="FTP_PASSWORD"):
            build_ctx(env="dev", config_dir=tmp_path)

    def test_builds_ctx_successfully(self, tmp_path: Path, monkeypatch):
        """Valid config and env var produces a populated AppContext."""
        monkeypatch.setenv("FTP_PASSWORD", "secret")
        config_content = """
logging:
  level: DEBUG
  log_dir: logs
  app_name: ftp_sync
ftp:
  host: ftp.example.com
  port: 21
  user: user
sync:
  remote_paths: [/incoming/]
  local_destination: C:/downloads
  state_file: state.json
  chunk_size: 10
filters:
  extensions: [csv]
  name_pattern: null
  max_age_days: null
"""
        (tmp_path / "config.dev.yaml").write_text(config_content, encoding="utf-8")
        ctx = build_ctx(env="dev", config_dir=tmp_path)

        assert ctx.env == "dev"
        assert ctx.ftp_host == "ftp.example.com"
        assert ctx.ftp_password == "secret"
        assert ctx.filter_extensions == [".csv"]
        assert ctx.chunk_size == 10
