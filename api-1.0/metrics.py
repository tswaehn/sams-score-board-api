from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Any
from urllib.parse import quote_plus

import requests

from server_config import (
    HOST,
    INFLUXDB_BUCKET,
    INFLUXDB_ENABLED,
    INFLUXDB_ORG,
    INFLUXDB_TIMEOUT_SECONDS,
    INFLUXDB_TOKEN,
    INFLUXDB_URL,
    PORT,
)


LOGGER = logging.getLogger("api.metrics")
NANOSECONDS_PER_MINUTE = 60 * 1_000_000_000


def _escape_key(value: str) -> str:
    return value.replace("\\", "\\\\").replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")


def _escape_string_field(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _format_line(
    measurement: str,
    *,
    tags: dict[str, str] | None = None,
    fields: dict[str, Any],
    timestamp_ns: int | None = None,
) -> str:
    if not fields:
        raise RuntimeError("InfluxDB line protocol requires at least one field")

    measurement_part = _escape_key(measurement)
    if tags:
        tag_parts = [
            f"{_escape_key(str(key))}={_escape_key(str(value))}"
            for key, value in sorted(tags.items())
            if value is not None
        ]
        if tag_parts:
            measurement_part = f"{measurement_part},{','.join(tag_parts)}"

    field_parts: list[str] = []
    for key, value in sorted(fields.items()):
        escaped_key = _escape_key(str(key))
        if isinstance(value, bool):
            field_parts.append(f"{escaped_key}={'true' if value else 'false'}")
        elif isinstance(value, int) and not isinstance(value, bool):
            field_parts.append(f"{escaped_key}={value}i")
        elif isinstance(value, float):
            field_parts.append(f"{escaped_key}={value}")
        else:
            field_parts.append(f'{escaped_key}="{_escape_string_field(str(value))}"')

    if timestamp_ns is None:
        timestamp_ns = time.time_ns()

    return f"{measurement_part} {','.join(field_parts)} {timestamp_ns}"


def _current_day_key() -> str:
    return time.strftime("%Y-%m-%d", time.localtime())


class InfluxMetricsClient:
    def __init__(self) -> None:
        self._enabled = bool(
            INFLUXDB_ENABLED and INFLUXDB_URL and INFLUXDB_ORG and INFLUXDB_BUCKET and INFLUXDB_TOKEN
        )
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._unique_client_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._warned_unconfigured = False
        self._unique_client_lock = threading.Lock()
        self._active_unique_client_bucket = int(time.time() // 60)
        self._active_unique_client_ids: set[str] = set()
        self._active_daily_unique_client_day = _current_day_key()
        self._active_daily_unique_client_ids: set[str] = set()
        self._last_daily_unique_emit_bucket = self._active_unique_client_bucket - 1

    def start(self) -> None:
        if not self._enabled:
            if INFLUXDB_ENABLED and not self._warned_unconfigured:
                LOGGER.warning("InfluxDB metrics enabled but configuration is incomplete; metrics disabled")
                self._warned_unconfigured = True
            return

        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="influxdb-metrics",
            daemon=True,
        )
        self._thread.start()
        self._unique_client_thread = threading.Thread(
            target=self._run_unique_client_metrics,
            name="influxdb-unique-client-metrics",
            daemon=True,
        )
        self._unique_client_thread.start()

    def stop(self) -> None:
        if not self._enabled:
            return

        self._stop_event.set()
        self._queue.put(None)
        if self._thread is not None:
            self._thread.join(timeout=2)
        if self._unique_client_thread is not None:
            self._unique_client_thread.join(timeout=2)

    def record_http_request(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        self.write_point(
            "http_requests",
            tags={
                "method": method,
                "path": path,
                "status_code": str(status_code),
                "host": HOST,
            },
            fields={
                "count": 1,
                "duration_ms": float(duration_ms),
                "port": int(PORT),
            },
        )

    def record_unique_client_session(self, client_id: str | None) -> None:
        if not self._enabled or not client_id:
            return

        with self._unique_client_lock:
            self._flush_completed_unique_client_buckets_locked(int(time.time() // 60))
            self._rotate_daily_unique_client_day_locked(_current_day_key())
            self._active_unique_client_ids.add(client_id)
            self._active_daily_unique_client_ids.add(client_id)

    def record_upstream_request(
        self,
        *,
        method: str,
        endpoint: str,
        status_code: int,
        duration_ms: float,
        page: int,
        success: bool,
    ) -> None:
        self.write_point(
            "upstream_requests",
            tags={
                "method": method,
                "endpoint": endpoint,
                "status_code": str(status_code),
                "success": str(success).lower(),
            },
            fields={
                "count": 1,
                "duration_ms": float(duration_ms),
                "page": int(page),
            },
        )

    def _run(self) -> None:
        write_url = (
            f"{INFLUXDB_URL.rstrip('/')}/api/v2/write"
            f"?org={quote_plus(str(INFLUXDB_ORG))}"
            f"&bucket={quote_plus(str(INFLUXDB_BUCKET))}"
            f"&precision=ns"
        )
        headers = {
            "Authorization": f"Token {INFLUXDB_TOKEN}",
            "Content-Type": "text/plain; charset=utf-8",
        }
        session = requests.Session()

        while True:
            line = self._queue.get()
            if line is None:
                break

            lines = [line]
            while True:
                try:
                    queued_line = self._queue.get_nowait()
                except queue.Empty:
                    break

                if queued_line is None:
                    self._queue.put(None)
                    break

                lines.append(queued_line)

            try:
                response = session.post(
                    write_url,
                    headers=headers,
                    data="\n".join(lines),
                    timeout=INFLUXDB_TIMEOUT_SECONDS,
                )
                response.raise_for_status()
            except Exception as exc:
                LOGGER.warning("Failed to write metrics to InfluxDB: %s", exc)

    def _run_unique_client_metrics(self) -> None:
        while not self._stop_event.wait(timeout=1.0):
            self._flush_due_unique_client_metrics()

        self._flush_due_unique_client_metrics(finalize_current_bucket=True)

    def _flush_completed_unique_client_buckets_locked(self, target_bucket: int) -> None:
        while self._active_unique_client_bucket < target_bucket:
            self._write_unique_client_bucket_locked(self._active_unique_client_bucket)
            self._active_unique_client_bucket += 1
            self._active_unique_client_ids = set()

    def _write_unique_client_bucket_locked(self, bucket: int) -> None:
        self.write_point(
            "unique_client_sessions",
            tags={
                "host": HOST,
            },
            fields={
                "count": len(self._active_unique_client_ids),
                "port": int(PORT),
            },
            timestamp_ns=bucket * NANOSECONDS_PER_MINUTE,
        )

    def _rotate_daily_unique_client_day_locked(self, current_day: str) -> None:
        if self._active_daily_unique_client_day == current_day:
            return

        self._active_daily_unique_client_day = current_day
        self._active_daily_unique_client_ids = set()

    def _write_daily_unique_client_count_locked(self, bucket: int) -> None:
        self.write_point(
            "unique_client_sessions_daily",
            tags={
                "host": HOST,
                "day": self._active_daily_unique_client_day,
            },
            fields={
                "count": len(self._active_daily_unique_client_ids),
                "port": int(PORT),
            },
            timestamp_ns=bucket * NANOSECONDS_PER_MINUTE,
        )

    def _flush_due_unique_client_metrics(self, *, finalize_current_bucket: bool = False) -> None:
        if not self._enabled:
            return

        with self._unique_client_lock:
            current_bucket = int(time.time() // 60)
            current_day = _current_day_key()
            self._flush_completed_unique_client_buckets_locked(current_bucket)
            self._rotate_daily_unique_client_day_locked(current_day)
            while self._last_daily_unique_emit_bucket < current_bucket:
                self._last_daily_unique_emit_bucket += 1
                self._write_daily_unique_client_count_locked(self._last_daily_unique_emit_bucket)
            if finalize_current_bucket and self._active_unique_client_ids:
                self._write_unique_client_bucket_locked(self._active_unique_client_bucket)
                self._active_unique_client_bucket = current_bucket + 1
                self._active_unique_client_ids = set()

    def write_point(
        self,
        measurement: str,
        *,
        tags: dict[str, str] | None = None,
        fields: dict[str, Any],
        timestamp_ns: int | None = None,
    ) -> None:
        if not self._enabled:
            return

        self._queue.put(_format_line(measurement, tags=tags, fields=fields, timestamp_ns=timestamp_ns))


METRICS = InfluxMetricsClient()
