"""Asynchronous persistence for internal operational logs."""

from __future__ import annotations

import logging
import queue
import threading

from database import Database


LOGGER = logging.getLogger("api2.internal-log")


class InternalLogWriter:
    def __init__(self, database: Database) -> None:
        self.database = database
        self._entries: queue.Queue[tuple[str, str, str | None, float | None] | None] = queue.Queue()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="internal-log-writer", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._entries.put(None)
        if self._thread:
            self._thread.join(timeout=5)

    def record_slow_request(self, request_url: str, duration_ms: float) -> None:
        self._entries.put((
            "error",
            f"Upstream request exceeded 5 seconds (durationMs={duration_ms:.1f})",
            request_url,
            duration_ms,
        ))

    def _run(self) -> None:
        while True:
            entry = self._entries.get()
            if entry is None:
                return
            severity, message, request_url, duration_ms = entry
            try:
                self.database.insert_internal_log(
                    severity=severity,
                    message=message,
                    request_url=request_url,
                    duration_ms=duration_ms,
                )
            except Exception:
                LOGGER.exception("Failed to persist internal log entry")
