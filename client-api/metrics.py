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


class InfluxMetricsClient:
    def __init__(self) -> None:
        self._enabled = bool(
            INFLUXDB_ENABLED and INFLUXDB_URL and INFLUXDB_ORG and INFLUXDB_BUCKET and INFLUXDB_TOKEN
        )
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._warned_unconfigured = False

    def start(self) -> None:
        if not self._enabled:
            if INFLUXDB_ENABLED and not self._warned_unconfigured:
                LOGGER.warning("InfluxDB metrics enabled but configuration is incomplete; metrics disabled")
                self._warned_unconfigured = True
            return

        if self._thread is not None and self._thread.is_alive():
            return

        self._thread = threading.Thread(
            target=self._run,
            name="influxdb-metrics",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        if not self._enabled:
            return

        self._queue.put(None)
        if self._thread is not None:
            self._thread.join(timeout=2)

    def write_point(
        self,
        measurement: str,
        *,
        tags: dict[str, str] | None = None,
        fields: dict[str, Any],
    ) -> None:
        if not self._enabled:
            return

        self._queue.put(_format_line(measurement, tags=tags, fields=fields))

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


METRICS = InfluxMetricsClient()
