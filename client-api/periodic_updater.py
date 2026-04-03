from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any


class PeriodicUpdater:
    def __init__(
        self,
        *,
        logger_name: str,
        thread_name: str,
        store_file_name: str,
        ttl_seconds: float,
    ) -> None:
        self.lock = threading.RLock()
        self.store: dict[str, Any] = {}
        self.store_item_stored_at: dict[str, float] = {}
        self.stored_at: float | None = None
        self.ttl_seconds = ttl_seconds
        self.logger = logging.getLogger(logger_name)
        self.store_file_path = Path(__file__).with_name("cache") / store_file_name
        self.thread_name = thread_name
        self.inflight_updates: dict[str, threading.Event] = {}
        self.load_store()

    def on_store_loaded(self) -> None:
        pass

    def update_store(self, uuid: str | None = None) -> None:
        raise NotImplementedError

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
            "storeItemStoredAt": self.store_item_stored_at,
        }
        self._write_json_file(self.store_file_path, payload)

    def dump_raw_json(self, file_name: str, uuid: str, payload: dict[str, Any]) -> None:
        raw_file_path = self.store_file_path.parent / file_name
        raw_payload: dict[str, Any] = {}

        if raw_file_path.exists():
            try:
                loaded_payload = json.loads(raw_file_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self.logger.warning("Failed to load raw json store: %s", raw_file_path)
            else:
                if isinstance(loaded_payload, dict):
                    raw_payload = loaded_payload
                else:
                    self.logger.warning("Raw json store has invalid shape: %s", raw_file_path)

        raw_payload[uuid] = payload
        self._write_json_file(raw_file_path, raw_payload)

    def replace_store(self, store: dict[str, Any]) -> None:
        with self.lock:
            stored_at = time.time()
            self.store = store
            self.store_item_stored_at = {
                key: stored_at
                for key in store
            }
            self.stored_at = stored_at
            self._persist_store()
            self.on_store_loaded()

    def set_store_item(self, key: str, value: Any) -> None:
        with self.lock:
            stored_at = time.time()
            self.store[key] = value
            self.store_item_stored_at[key] = stored_at
            self.stored_at = stored_at
            self._persist_store()
            self.on_store_loaded()

    def get_store_item(self, key: str) -> Any:
        with self.lock:
            return self.store.get(key)

    def get_store_item_stored_at(self, key: str) -> float | None:
        with self.lock:
            stored_at = self.store_item_stored_at.get(key)
            return stored_at if isinstance(stored_at, (int, float)) else None

    def wait_for_uuid(self, uuid: str | None = None) -> None:
        update_key = uuid if uuid is not None else "__all__"

        while True:
            should_update = False

            with self.lock:
                if uuid is None:
                    if not self.is_store_expired():
                        return
                else:
                    store_item = self.store.get(uuid)
                    if store_item is not None and not self.is_store_item_expired(uuid):
                        return

                update_event = self.inflight_updates.get(update_key)
                if update_event is None:
                    update_event = threading.Event()
                    self.inflight_updates[update_key] = update_event
                    should_update = True

            if not should_update:
                update_event.wait()
                continue

            try:
                self.update_store(uuid)
            finally:
                with self.lock:
                    current_update_event = self.inflight_updates.pop(update_key, None)
                    if current_update_event is not None:
                        current_update_event.set()
            return

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
        item_timestamps = payload.get("storeItemStoredAt")
        if isinstance(item_timestamps, dict):
            self.store_item_stored_at = {
                key: value
                for key, value in item_timestamps.items()
                if isinstance(key, str) and isinstance(value, (int, float))
            }
        elif self.stored_at is not None:
            self.store_item_stored_at = {
                key: self.stored_at
                for key in self.store
            }
        else:
            self.store_item_stored_at = {}
        self.on_store_loaded()

    def is_store_expired(self) -> bool:
        if self.stored_at is None:
            return True
        return time.time() - self.stored_at > self.ttl_seconds

    def is_store_item_expired(self, key: str) -> bool:
        stored_at = self.get_store_item_stored_at(key)
        if stored_at is None:
            return True
        return time.time() - stored_at > self.ttl_seconds
