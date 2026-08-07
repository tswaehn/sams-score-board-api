"""Runtime configuration loaded from SERVER_CONFIG_PATH."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


SERVER_CONFIG_PATH = os.getenv("SERVER_CONFIG_PATH", "config/server_config.json")


def _load_config(path: str) -> dict[str, Any]:
    config_file = Path(path)
    if not config_file.exists():
        raise RuntimeError(f"Configured SERVER_CONFIG_PATH does not exist: {path}")
    try:
        value = json.loads(config_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse server config JSON: {path}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("Server config must be a JSON object")
    return value


def _required(config: dict[str, Any], key: str) -> str:
    value = config.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"Missing or empty required config key: {key}")
    return value.strip()


CONFIG = _load_config(SERVER_CONFIG_PATH)
HOST = str(CONFIG.get("host", "0.0.0.0"))
PORT = int(CONFIG.get("port", 8001))
LOG_LEVEL = str(CONFIG.get("log_level", "info"))
DATABASE_PATH = str(CONFIG.get("database_path", "data/sams-database"))
SSVB_API_URL = _required(CONFIG, "ssvb_api_url").rstrip("/")
SSVB_API_KEY = _required(CONFIG, "ssvb_api_key")
UPSTREAM_MIN_DELAY_SECONDS = float(CONFIG.get("upstream_min_delay_seconds", 0.3))
UPSTREAM_MAX_RETRIES = int(CONFIG.get("upstream_max_retries", 3))
HISTORICAL_SYNC_INTERVAL_SECONDS = int(CONFIG.get("historical_sync_interval_seconds", 24 * 60 * 60))
