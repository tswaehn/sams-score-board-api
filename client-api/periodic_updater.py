from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable


class PeriodicUpdater:
    def __init__(
        self,
        *,
        logger_name: str,
        thread_name: str,
        store_file_name: str,
        ttl_seconds: float,
        update_callback: Callable[[], None],
    ) -> None:
        self.lock = threading.RLock()
        self.store: dict[str, Any] = {}
        self.stored_at: float | None = None
        self.ttl_seconds = ttl_seconds
        self.update_callback = update_callback
        self.idle_loop_entered = threading.Event()
        self.logger = logging.getLogger(logger_name)
        self.store_file_path = Path(__file__).with_name("cache") / store_file_name
        self.load_store()
        self.update_thread = threading.Thread(
            target=self.run_update_loop,
            name=thread_name,
            daemon=True,
        )
        self.update_thread.start()

    def on_store_loaded(self) -> None:
        pass

    def _write_json_file(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _persist_store(self) -> None:
        payload = {
            "storedAt": self.stored_at,
            "store": self.store,
        }
        self._write_json_file(self.store_file_path, payload)

    def dump_raw_json(self, file_name: str, payload: Any) -> None:
        raw_file_path = self.store_file_path.parent / file_name
        self._write_json_file(raw_file_path, payload)

    def replace_store(self, store: dict[str, Any]) -> None:
        with self.lock:
            self.store = store
            self.stored_at = time.time()
            self._persist_store()
            self.on_store_loaded()

    def set_store_item(self, key: str, value: Any) -> None:
        with self.lock:
            self.store[key] = value
            self.stored_at = time.time()
            self._persist_store()

    def get_store_item(self, key: str) -> Any:
        with self.lock:
            return self.store.get(key)

    def wait_until_store_loaded(self) -> None:
        self.idle_loop_entered.wait()

    def load_store(self) -> None:
        if not self.store_file_path.exists():
            return

        try:
            payload = json.loads(self.store_file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.logger.warning("Failed to load persisted store: %s", self.store_file_path)
            return

        if not isinstance(payload, dict) or not isinstance(payload.get("store"), dict):
            self.logger.warning("Persisted store file has invalid shape: %s", self.store_file_path)
            return

        self.store = payload["store"]
        stored_at = payload.get("storedAt")
        self.stored_at = stored_at if isinstance(stored_at, (int, float)) else None
        self.on_store_loaded()

    def is_store_expired(self) -> bool:
        if self.stored_at is None:
            return True
        return time.time() - self.stored_at > self.ttl_seconds

    def seconds_until_next_update(self) -> float:
        now = datetime.now()
        next_update = now.replace(hour=1, minute=0, second=0, microsecond=0)
        if now >= next_update:
            next_update = next_update + timedelta(days=1)
        return max((next_update - now).total_seconds(), 0.0)

    def run_update_loop(self) -> None:
        if self.is_store_expired():
            try:
                self.update_callback()
            except Exception:
                self.logger.exception("Background update failed")
        else:
            self.logger.info(
                "Skipping startup update because persisted store is still fresh"
            )

        self.idle_loop_entered.set()

        while True:
            sleep_seconds = self.seconds_until_next_update()
            self.logger.info(
                "Background update completed; next run in %.0f seconds",
                sleep_seconds,
            )
            time.sleep(sleep_seconds)
            try:
                self.update_callback()
            except Exception:
                self.logger.exception("Background update failed")
