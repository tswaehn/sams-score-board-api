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
import re
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

import requests


LOGGER = logging.getLogger("api2.upstream")
REQUEST_TIMEOUT_SECONDS = 10
REQUEST_CACHE_PATH = Path(__file__).with_name("data") / "sams-request-cache"
LEGACY_REQUEST_CACHE_DIR = Path(__file__).with_name("data") / "request-cache"
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

    def __init__(
        self,
        path: Path = REQUEST_CACHE_PATH,
        legacy_cache_dir: Path = LEGACY_REQUEST_CACHE_DIR,
        base_url: str | None = None,
    ) -> None:
        self.path = path
        self.legacy_cache_dir = legacy_cache_dir
        self.base_url = base_url.rstrip("/") if base_url else None
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
                          legacy_cache_filename TEXT UNIQUE
                        );
                        CREATE INDEX IF NOT EXISTS upstream_requests_url_idx ON upstream_requests(url);
                        CREATE TABLE IF NOT EXISTS request_cache_migrations (
                          name TEXT PRIMARY KEY,
                          applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                        );
                        """
                    )
                    migration_name = "import-request-cache-files-v2"
                    already_migrated = connection.execute(
                        "SELECT 1 FROM request_cache_migrations WHERE name = ?", (migration_name,)
                    ).fetchone()
                    if not already_migrated and self._migrate_legacy_files(connection):
                        connection.execute("INSERT INTO request_cache_migrations (name) VALUES (?)", (migration_name,))
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

    def _migrate_legacy_files(self, connection: sqlite3.Connection) -> bool:
        """Import the former file cache once without deleting the source files.

        The old cache only receives upstream_sync endpoints, whose URL shapes are
        known. That lets the migration reverse the sanitized filenames exactly.
        """
        if not self.legacy_cache_dir.is_dir():
            return True
        completed = True
        for cache_file in sorted(self.legacy_cache_dir.glob("*.json")):
            try:
                response_body = cache_file.read_text(encoding="utf-8")
            except OSError:
                LOGGER.exception("Failed to read legacy upstream cache file: %s", cache_file)
                completed = False
                continue
            filename = cache_file.name
            request_url = _restore_legacy_request_url(filename, self.base_url)
            if request_url is None:
                LOGGER.warning("Unable to reconstruct URL from legacy upstream cache file: %s", cache_file)
                completed = False
                continue
            connection.execute(
                """INSERT OR IGNORE INTO upstream_requests
                   (url, request, response, legacy_cache_filename)
                   VALUES (?, ?, ?, ?)""",
                (
                    request_url,
                    json.dumps(
                        {"method": "GET", "url": request_url, "legacyCacheFilename": filename},
                        separators=(",", ":"),
                    ),
                    response_body,
                    filename,
                ),
            )
        return completed


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


_UUID_PATTERN = r"(?P<uuid>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
_LEGACY_COLLECTION_PATTERNS = (
    (re.compile(r"^seasons_page_(?P<page>\d+)_size_100$"), "seasons?page={page}&size=100"),
    (re.compile(rf"^(?P<entity>competitions|leagues)_season_{_UUID_PATTERN}_page_(?P<page>\d+)_size_100$"), "{entity}?season={uuid}&page={page}&size=100"),
    (re.compile(rf"^(?P<entity>competitions|leagues)_{_UUID_PATTERN}_teams_page_(?P<page>\d+)_size_100$"), "{entity}/{uuid}/teams?page={page}&size=100"),
    (re.compile(rf"^competitions_{_UUID_PATTERN}_match-groups_page_(?P<page>\d+)_size_100$"), "competitions/{uuid}/match-groups?page={page}&size=100"),
    (re.compile(rf"^match-groups_{_UUID_PATTERN}_competition-matches_page_(?P<page>\d+)_size_100$"), "match-groups/{uuid}/competition-matches?page={page}&size=100"),
    (re.compile(rf"^competitions_{_UUID_PATTERN}_rankings_page_(?P<page>\d+)_size_100$"), "competitions/{uuid}/rankings?page={page}&size=100"),
    (re.compile(rf"^leagues_{_UUID_PATTERN}_match-days_page_(?P<page>\d+)_size_100$"), "leagues/{uuid}/match-days?page={page}&size=100"),
    (re.compile(rf"^match-days_{_UUID_PATTERN}_league-matches_page_(?P<page>\d+)_size_100$"), "match-days/{uuid}/league-matches?page={page}&size=100"),
    (re.compile(rf"^leagues_{_UUID_PATTERN}_rankings_page_(?P<page>\d+)_size_100$"), "leagues/{uuid}/rankings?page={page}&size=100"),
)
_LEGACY_DETAIL_PATTERN = re.compile(rf"^(?P<entity>competitions|leagues|seasons|associations|teams)_{_UUID_PATTERN}$")


def _restore_legacy_request_url(filename: str, base_url: str | None) -> str | None:
    if not base_url or not filename.endswith(".json"):
        return None
    prefix = _sanitize_request_cache_name(base_url)
    stem = filename[:-5]
    if not stem.startswith(f"{prefix}_"):
        return None
    endpoint_name = stem[len(prefix) + 1:]
    for pattern, endpoint_template in _LEGACY_COLLECTION_PATTERNS:
        match = pattern.fullmatch(endpoint_name)
        if match:
            return f"{base_url}/{endpoint_template.format(**match.groupdict())}"
    match = _LEGACY_DETAIL_PATTERN.fullmatch(endpoint_name)
    if match:
        return f"{base_url}/{match.group('entity')}/{match.group('uuid')}"
    return None


def _sanitize_request_cache_name(request_url: str) -> str:
    """Match the filename transformation used by the retired file cache."""
    parsed = urlsplit(request_url.strip())
    raw_name = "_".join(
        part for part in (parsed.scheme, parsed.netloc, parsed.path, parsed.query, parsed.fragment) if part
    )
    return re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9._-]+", "_", raw_name)).strip("._-")


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
        self.request_cache = request_cache or SamsRequestCache(base_url=self.base_url)
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
