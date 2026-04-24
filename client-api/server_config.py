from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


SERVER_CONFIG_PATH = os.getenv("SERVER_CONFIG_PATH")


def _load_config_file(config_path: str | None) -> dict[str, Any]:
    if not config_path:
        return {}

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


def _env_or_config(
    env_name: str,
    config: dict[str, Any],
    config_key: str,
    default: Any = None,
) -> Any:
    env_value = os.getenv(env_name)
    if env_value is not None:
        return env_value

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


CONFIG_FILE = _load_config_file(SERVER_CONFIG_PATH)

TIMEZONE = _env_or_config("TZ", CONFIG_FILE, "tz")
if TIMEZONE:
    os.environ["TZ"] = str(TIMEZONE)
    if hasattr(time, "tzset"):
        time.tzset()

HOST = str(_env_or_config("HOST", CONFIG_FILE, "host", "0.0.0.0"))
PORT = int(_env_or_config("PORT", CONFIG_FILE, "port", 8000))
LOG_LEVEL = str(_env_or_config("LOG_LEVEL", CONFIG_FILE, "log_level", "info")).lower()
SSVB_API_KEY = _env_or_config("SSVB_API_KEY", CONFIG_FILE, "ssvb_api_key")
LIVE_API_URLS = _normalize_live_api_urls(
    _env_or_config("LIVE_API_URLS", CONFIG_FILE, "live_api_urls", [])
)
LIVE_API_SNAPSHOT_REFRESH_SECONDS = int(
    _env_or_config(
        "LIVE_API_SNAPSHOT_REFRESH_SECONDS",
        CONFIG_FILE,
        "live_api_snapshot_refresh_seconds",
        60,
    )
)
