"""Asynchronous append-only file logging for internal operational events."""

from __future__ import annotations

import logging
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path

LOGGER = logging.getLogger("api2.internal-log")


class InternalLogWriter:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
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

    def record_request_time(self, request_url: str, duration_ms: float, success: bool) -> None:
        is_slow = duration_ms > 5_000
        self._entries.put((
            "error" if is_slow or not success else "info",
            (
                f"Upstream request exceeded 5 seconds (durationMs={duration_ms:.1f})"
                if is_slow
                else f"Upstream request failed (durationMs={duration_ms:.1f})"
                if not success
                else f"Upstream request completed (durationMs={duration_ms:.1f})"
            ),
            request_url,
            duration_ms,
        ))

    def record_request_timeout(
        self, request_url: str, duration_ms: float, attempt: int, max_attempts: int
    ) -> None:
        self._entries.put((
            "error",
            f"Upstream request timed out (durationMs={duration_ms:.1f}, attempt={attempt}/{max_attempts})",
            request_url,
            duration_ms,
        ))

    def record_collection_failure(self, endpoint: str, error: Exception) -> None:
        """Record when sync deliberately falls back to an empty upstream collection."""
        self._entries.put((
            "error",
            f"Upstream collection fetch failed; returning empty result (error={error})",
            endpoint,
            0.0,
        ))

    def record_startup(self) -> None:
        self._entries.put(("info", "SAMS scoreboard API starting", None, 0.0))

    def _run(self) -> None:
        try:
            with self.path.open("a", encoding="utf-8") as log_file:
                while True:
                    entry = self._entries.get()
                    if entry is None:
                        return
                    severity, message, request_url, duration_ms = entry
                    timestamp = datetime.now(timezone.utc).isoformat()
                    log_file.write(
                        f"{timestamp} severity={severity} durationMs={duration_ms:.1f} "
                        f"url={request_url} message={message}\n"
                    )
                    log_file.flush()
        except OSError:
            LOGGER.exception("Failed to write internal log file: %s", self.path)
