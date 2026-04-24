from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any
from server_config import WRITE_RAW_CACHE


class PeriodicUpdater:
    def __init__(
        self,
        *,
        logger_name: str,
        thread_name: str,
        store_file_name: str,
    ) -> None:
        self.lock = threading.RLock()
        self.store: dict[str, Any] = {}
        self.store_item_expires_at: dict[str, float] = {}
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
            "store": self.store,
            "storeItemExpiresAt": self.store_item_expires_at,
        }
        self._write_json_file(self.store_file_path, payload)

    def dump_raw_json(self, file_name: str, uuid: str, payload: dict[str, Any]) -> None:
        if not WRITE_RAW_CACHE:
            return

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

    def dump_raw_store(self, file_name: str, payload: dict[str, Any]) -> None:
        if not WRITE_RAW_CACHE:
            return

        raw_file_path = self.store_file_path.parent / file_name
        self._write_json_file(raw_file_path, payload)

    def replace_store(self, store: dict[str, Any], ttl_seconds: float) -> None:
        with self.lock:
            expires_at = time.time() + ttl_seconds
            self.store = store
            self.store_item_expires_at = {
                key: expires_at
                for key in store
            }
            self._persist_store()
            self.on_store_loaded()

    def set_store_item(self, key: str, value: Any, ttl_seconds: float) -> None:
        with self.lock:
            self.store[key] = value
            self.store_item_expires_at[key] = time.time() + ttl_seconds
            self._persist_store()
            self.on_store_loaded()

    def get_store_item(self, key: str) -> Any:
        with self.lock:
            return self.store.get(key)

    def get_store_item_expires_at(self, key: str) -> float | None:
        with self.lock:
            expires_at = self.store_item_expires_at.get(key)
            return expires_at if isinstance(expires_at, (int, float)) else None

    def _run_coalesced_update(self, uuid: str | None = None) -> bool:
        update_key = uuid if uuid is not None else "__all__"

        with self.lock:
            update_event = self.inflight_updates.get(update_key)
            if update_event is None:
                update_event = threading.Event()
                self.inflight_updates[update_key] = update_event
                should_update = True
            else:
                should_update = False

        if not should_update:
            update_event.wait()
            return False

        try:
            self.update_store(uuid)
        finally:
            with self.lock:
                current_update_event = self.inflight_updates.pop(update_key, None)
                if current_update_event is not None:
                    current_update_event.set()

        return True

    def wait_for_uuid(self, uuid: str | None = None) -> None:
        while True:
            with self.lock:
                if uuid is None:
                    if not self.is_store_expired():
                        return
                else:
                    store_item = self.store.get(uuid)
                    if store_item is not None and not self.is_store_item_expired(uuid):
                        return

            if self._run_coalesced_update(uuid):
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
        item_expirations = payload.get("storeItemExpiresAt")
        self.store_item_expires_at = {
            key: value
            for key, value in item_expirations.items()
            if isinstance(key, str) and isinstance(value, (int, float))
        } if isinstance(item_expirations, dict) else {}
        self.on_store_loaded()

    def is_store_expired(self) -> bool:
        with self.lock:
            if not self.store:
                return True
            now = time.time()
            return any(
                not isinstance(self.store_item_expires_at.get(key), (int, float))
                or now > self.store_item_expires_at[key]
                for key in self.store
            )

    def is_store_item_expired(self, key: str) -> bool:
        expires_at = self.get_store_item_expires_at(key)
        if expires_at is None:
            return True
        return time.time() > expires_at
