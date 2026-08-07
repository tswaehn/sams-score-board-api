"""The sole gateway for upstream REST requests.

One worker deliberately serializes calls: it protects SAMS from bursts and gives the
syncer one observable, FIFO queue instead of scattered direct `requests.get` calls.
"""

from __future__ import annotations

from concurrent.futures import Future
from dataclasses import dataclass, field
import itertools
import logging
import queue
import threading
import time
from typing import Any

import requests


LOGGER = logging.getLogger("api2.upstream")
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
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.min_delay_seconds = min_delay_seconds
        self.max_retries = max(0, max_retries)
        self._requests: queue.PriorityQueue[UpstreamRequest] = queue.PriorityQueue()
        self._sequence = itertools.count()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
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
                payload = self._request_with_retries(request.endpoint)
                request.future.set_result(payload)
            except RuntimeError as exc:
                request.future.set_exception(exc)
            except Exception as exc:
                request.future.set_exception(RuntimeError(f"Upstream request failed for {request.endpoint}: {exc}"))
            finally:
                next_request_at = time.monotonic() + self.min_delay_seconds

    def _request_with_retries(self, endpoint: str) -> dict[str, Any] | list[Any]:
        url = f"{self.base_url}/{endpoint}"
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                # A new session avoids reusing a socket that the upstream has closed.
                with requests.Session() as session:
                    response = session.get(
                        url,
                        headers={**DEFAULT_HEADERS, "X-Api-Key": self.api_key},
                        timeout=30,
                    )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, (dict, list)):
                    raise RuntimeError("Upstream response was not a JSON object or array")
                return payload
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
