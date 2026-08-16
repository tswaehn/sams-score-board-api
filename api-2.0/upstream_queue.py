"""The sole gateway for upstream REST requests.

One worker deliberately serializes calls: it protects SAMS from bursts and gives the
syncer one observable, FIFO queue instead of scattered direct `requests.get` calls.
"""

from __future__ import annotations

from concurrent.futures import Future
from dataclasses import dataclass, field
import json
import itertools
import logging
import queue
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Callable

import requests


LOGGER = logging.getLogger("api2.upstream")
REQUEST_TIMEOUT_SECONDS = 10
REQUEST_CACHE_PATH = Path(__file__).with_name("data") / "sams-request-cache.sqlite3"
DEFAULT_HEADERS = {
    "Accept": "*/*",
    # SAMS may close reused keep-alive connections without a response.  Request a
    # fresh connection for every serialized request, as API 1.0 does.
    "Connection": "close",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.0 Safari/537.36"
    ),
}


class SamsRequestCache:
    """Append-only SQLite log of successful SAMS requests and responses."""

    def __init__(self, path: Path = REQUEST_CACHE_PATH) -> None:
        self.path = path
        self._initialized = False
        self._lock = threading.Lock()

    def initialize(self) -> bool:
        with self._lock:
            if self._initialized:
                return True
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with sqlite3.connect(self.path) as connection:
                    connection.executescript(
                        """
                        CREATE TABLE IF NOT EXISTS upstream_requests (
                          id INTEGER PRIMARY KEY,
                          url TEXT NOT NULL,
                          request TEXT NOT NULL,
                          response TEXT NOT NULL,
                          logged_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                          last_access TEXT
                        );
                        CREATE INDEX IF NOT EXISTS upstream_requests_url_idx ON upstream_requests(url);
                        """
                    )
                    columns = {
                        row[1] for row in connection.execute("PRAGMA table_info(upstream_requests)")
                    }
                    if "last_access" not in columns:
                        connection.execute("ALTER TABLE upstream_requests ADD COLUMN last_access TEXT")
            except (OSError, sqlite3.Error):
                LOGGER.exception("Failed to initialize upstream request cache: %s", self.path)
                return False
            self._initialized = True
            return True

    def record(self, url: str, request: dict[str, Any], response_body: str) -> None:
        if not self.initialize():
            return
        try:
            with sqlite3.connect(self.path, timeout=30) as connection:
                connection.execute(
                    "INSERT INTO upstream_requests (url, request, response) VALUES (?, ?, ?)",
                    (url, json.dumps(request, separators=(",", ":"), ensure_ascii=False), response_body),
                )
        except sqlite3.Error:
            LOGGER.exception("Failed to write upstream request cache for %s", url)

    def get(self, url: str) -> dict[str, Any] | list[Any] | None:
        """Return the newest valid cached JSON response for an exact request URL."""
        if not self.initialize():
            return None
        try:
            with sqlite3.connect(self.path, timeout=30) as connection:
                row = connection.execute(
                    "SELECT id, response FROM upstream_requests WHERE url = ? ORDER BY id DESC LIMIT 1", (url,)
                ).fetchone()
        except sqlite3.Error:
            LOGGER.exception("Failed to read upstream request cache for %s", url)
            return None
        if row is None:
            return None
        try:
            payload = json.loads(row[1])
        except json.JSONDecodeError:
            LOGGER.warning("Ignoring invalid JSON in upstream request cache for %s", url)
            return None
        if not isinstance(payload, (dict, list)):
            return None
        try:
            with sqlite3.connect(self.path, timeout=30) as connection:
                connection.execute("UPDATE upstream_requests SET last_access = CURRENT_TIMESTAMP WHERE id = ?", (row[0],))
        except sqlite3.Error:
            LOGGER.exception("Failed to update upstream request cache access time for %s", url)
        return payload

def _serialize_request(request: requests.PreparedRequest) -> dict[str, Any]:
    """Return request metadata suitable for diagnostics without retaining the API key."""
    headers = {
        name: ("<redacted>" if name.lower() == "x-api-key" else value)
        for name, value in request.headers.items()
    }
    body = request.body
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    return {"method": request.method, "url": request.url, "headers": headers, "body": body}


@dataclass(order=True)
class UpstreamRequest:
    priority: int
    sequence: int
    endpoint: str = field(compare=False)
    future: Future[dict[str, Any] | list[Any]] = field(compare=False)


class UpstreamQueue:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        min_delay_seconds: float = 0.3,
        max_retries: int = 3,
        request_time_logger: Callable[[str, float, bool], None] | None = None,
        timeout_logger: Callable[[str, float, int, int], None] | None = None,
        request_cache: SamsRequestCache | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.min_delay_seconds = min_delay_seconds
        self.max_retries = max(0, max_retries)
        self.request_time_logger = request_time_logger
        self.timeout_logger = timeout_logger
        self.request_cache = request_cache or SamsRequestCache()
        self._requests: queue.PriorityQueue[UpstreamRequest] = queue.PriorityQueue()
        self._sequence = itertools.count()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self.request_cache.initialize()
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="sams-upstream-queue", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def request(self, endpoint: str, *, priority: int = 10) -> Future[dict[str, Any] | list[Any]]:
        normalized = endpoint.strip("/")
        if not normalized:
            raise ValueError("endpoint must not be empty")
        future: Future[dict[str, Any] | list[Any]] = Future()
        self._requests.put(UpstreamRequest(priority, next(self._sequence), normalized, future))
        return future

    def fetch(self, endpoint: str, *, priority: int = 10) -> dict[str, Any] | list[Any]:
        return self.request(endpoint, priority=priority).result()

    def fetch_cached(self, endpoint: str) -> dict[str, Any] | list[Any] | None:
        return self.request_cache.get(f"{self.base_url}/{endpoint.strip('/')}")

    @property
    def pending_count(self) -> int:
        return self._requests.qsize()

    def _run(self) -> None:
        next_request_at = 0.0
        while not self._stop.is_set():
            try:
                request = self._requests.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                time.sleep(max(0.0, next_request_at - time.monotonic()))
                started_at = time.monotonic()
                payload = self._request_with_retries(request.endpoint)
                request.future.set_result(payload)
                succeeded = True
            except RuntimeError as exc:
                succeeded = False
                request.future.set_exception(exc)
            except Exception as exc:
                succeeded = False
                request.future.set_exception(RuntimeError(f"Upstream request failed for {request.endpoint}: {exc}"))
            finally:
                duration_ms = (time.monotonic() - started_at) * 1000.0
                if self.request_time_logger is not None:
                    self.request_time_logger(
                        f"{self.base_url}/{request.endpoint}", duration_ms, succeeded
                    )
                next_request_at = time.monotonic() + self.min_delay_seconds

    def _request_with_retries(self, endpoint: str) -> dict[str, Any] | list[Any]:
        url = f"{self.base_url}/{endpoint}"
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            attempt_started_at = time.monotonic()
            try:
                # A new session avoids reusing a socket that the upstream has closed.
                with requests.Session() as session:
                    request_headers = {**DEFAULT_HEADERS, "X-Api-Key": self.api_key}
                    response = session.get(
                        url,
                        headers=request_headers,
                        timeout=REQUEST_TIMEOUT_SECONDS,
                    )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, (dict, list)):
                    raise RuntimeError("Upstream response was not a JSON object or array")
                self.request_cache.record(url, _serialize_request(response.request), response.text)
                return payload
            except requests.Timeout as exc:
                last_error = exc
                if self.timeout_logger is not None:
                    self.timeout_logger(
                        url,
                        (time.monotonic() - attempt_started_at) * 1000.0,
                        attempt + 1,
                        self.max_retries + 1,
                    )
                if attempt == self.max_retries:
                    break
                delay = min(2.0, 0.5 * (2 ** attempt))
                LOGGER.warning(
                    "Upstream request timed out endpoint=%s attempt=%s/%s; retrying in %.1fs: %s",
                    endpoint,
                    attempt + 1,
                    self.max_retries + 1,
                    delay,
                    exc,
                )
                time.sleep(delay)
            except (requests.RequestException, ValueError, RuntimeError) as exc:
                last_error = exc
                if attempt == self.max_retries:
                    break
                delay = min(2.0, 0.5 * (2 ** attempt))
                LOGGER.warning(
                    "Upstream request failed endpoint=%s attempt=%s/%s; retrying in %.1fs: %s",
                    endpoint,
                    attempt + 1,
                    self.max_retries + 1,
                    delay,
                    exc,
                )
                time.sleep(delay)
        raise RuntimeError(f"Upstream request failed for {endpoint} after {self.max_retries + 1} attempts: {last_error}")
