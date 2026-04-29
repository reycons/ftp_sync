"""Reads YAML config files and populates AppContext.

Responsibilities:
- Select the correct config file for the requested environment.
- Load secrets from .env (never from YAML).
- Construct and return a fully populated AppContext.

No business logic lives here.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from lib.ctx import AppContext

__all__ = ["build_ctx"]


def build_ctx(env: str, config_dir: Path) -> AppContext:
    """Load config for *env* and return a fully populated AppContext.

    Args:
        env:        Environment name — 'dev' or 'prod'.
        config_dir: Directory that contains config.{env}.yaml files.

    Returns:
        A populated AppContext ready for use.

    Raises:
        FileNotFoundError: If the config file for *env* does not exist.
        EnvironmentError:  If a required .env secret is missing.
        KeyError:          If a required config key is absent from the YAML.
    """
    # Load .env so that os.getenv() picks up secrets before we read config.
    _load_env_file(config_dir)

    config = _read_yaml(config_dir, env)

    return AppContext(
        env=env,
        log_level=_resolve_log_level(env, config),
        log_depth=0,
        log_dir=Path(config["logging"]["log_dir"]),
        app_name=config["logging"]["app_name"],
        chunk_size=int(config["sync"]["chunk_size"]),
        ftp_host=config["ftp"]["host"],
        ftp_port=int(config["ftp"]["port"]),
        ftp_user=config["ftp"]["user"],
        ftp_password=_require_env("FTP_PASSWORD"),
        remote_paths=list(config["sync"]["remote_paths"]),
        local_destination=Path(config["sync"]["local_destination"]),
        state_file=Path(config["sync"]["state_file"]),
        filter_extensions=_normalise_extensions(
            config.get("filters", {}).get("extensions", [])
        ),
        filter_name_pattern=config.get("filters", {}).get("name_pattern") or None,
        filter_max_age_days=config.get("filters", {}).get("max_age_days") or None,
        schedule_description=config.get("schedule", {}).get("description", ""),
    )


# ── Private helpers ───────────────────────────────────────────────────────────


def _load_env_file(config_dir: Path) -> None:
    """Load the .env file from the project root.

    .env is expected one level above config_dir if config lives in a
    subdirectory, or at the project root when config_dir IS the root.
    """
    # Try project root first, then config_dir itself.
    candidates = [config_dir / ".env", config_dir.parent / ".env"]
    for path in candidates:
        if path.exists():
            load_dotenv(dotenv_path=path, override=False)
            return


def _read_yaml(config_dir: Path, env: str) -> dict:
    """Read and parse the YAML config file for the given environment.

    Raises:
        FileNotFoundError: If config.{env}.yaml does not exist.
    """
    config_path = config_dir / f"config.{env}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}. "
            f"Expected 'config.{env}.yaml' in {config_dir}."
        )
    with config_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _resolve_log_level(env: str, config: dict) -> str:
    """Return the log level string from config, with a sensible per-env default.

    Explicit config value takes priority.  Fallback: DEBUG for dev, INFO for prod.
    """
    configured = config.get("logging", {}).get("level", "").upper()
    if configured in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        return configured
    return "DEBUG" if env == "dev" else "INFO"


def _require_env(var_name: str) -> str:
    """Return the value of an environment variable or raise if it is missing.

    Raises:
        EnvironmentError: If the variable is absent or empty.
    """
    value = os.getenv(var_name)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{var_name}' is not set. "
            "Add it to your .env file."
        )
    return value


def _normalise_extensions(extensions: list) -> list[str]:
    """Ensure every extension is lowercase and prefixed with a dot.

    Args:
        extensions: Raw list from YAML e.g. ['csv', '.TXT', 'xlsx'].

    Returns:
        Normalised list e.g. ['.csv', '.txt', '.xlsx'].
    """
    result: list[str] = []
    for ext in extensions:
        ext = str(ext).strip().lower()
        if ext and not ext.startswith("."):
            ext = f".{ext}"
        if ext:
            result.append(ext)
    return result
