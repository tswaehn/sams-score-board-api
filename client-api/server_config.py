from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


SERVER_CONFIG_PATH = os.getenv("SERVER_CONFIG_PATH")


def _load_config_file(config_path: str | None) -> dict[str, Any]:
    if not config_path:
        raise RuntimeError("SERVER_CONFIG_PATH is required")

    config_file = Path(config_path)
    if not config_file.exists():
        raise RuntimeError(f"Configured SERVER_CONFIG_PATH does not exist: {config_path}")

    try:
        payload = json.loads(config_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse server config JSON: {config_path}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError(f"Server config must be a JSON object: {config_path}")

    return payload


def _config_value(config: dict[str, Any], config_key: str, default: Any = None) -> Any:
    if config_key in config:
        return config[config_key]

    return default


def _normalize_live_api_urls(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        return [url.strip() for url in value.split(",") if url.strip()]

    if isinstance(value, list):
        urls: list[str] = []
        for item in value:
            if isinstance(item, str):
                stripped = item.strip()
                if stripped:
                    urls.append(stripped)
        return urls

    raise RuntimeError("live_api_urls must be a comma-separated string or an array of strings")


def _require_config_value(config: dict[str, Any], config_key: str) -> Any:
    value = _config_value(config, config_key)
    if value is None:
        raise RuntimeError(f"Missing required config key: {config_key}")

    if isinstance(value, str) and not value.strip():
        raise RuntimeError(f"Config key must not be empty: {config_key}")

    return value


CONFIG_FILE = _load_config_file(SERVER_CONFIG_PATH)

TIMEZONE = _config_value(CONFIG_FILE, "tz")
if TIMEZONE:
    os.environ["TZ"] = str(TIMEZONE)
    if hasattr(time, "tzset"):
        time.tzset()

HOST = str(_config_value(CONFIG_FILE, "host", "0.0.0.0"))
PORT = int(_config_value(CONFIG_FILE, "port", 8000))
LOG_LEVEL = str(_config_value(CONFIG_FILE, "log_level", "info")).lower()
SSVB_API_KEY = str(_require_config_value(CONFIG_FILE, "ssvb_api_key"))
LIVE_API_URLS = _normalize_live_api_urls(
    _require_config_value(CONFIG_FILE, "live_api_urls")
)
if not LIVE_API_URLS:
    raise RuntimeError("Config key live_api_urls must contain at least one URL")
LIVE_API_SNAPSHOT_REFRESH_SECONDS = int(
    _config_value(
        CONFIG_FILE,
        "live_api_snapshot_refresh_seconds",
        60,
    )
)
