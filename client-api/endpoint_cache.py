from __future__ import annotations

import json
import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qsl, urlparse
from uuid import UUID


LOGGER = logging.getLogger("competition-api.cache")
COLLECTION_CACHE_KEY = "_collection"
CACHE_DIR = Path(__file__).with_name("cache")
JsonPayload = dict | list


@dataclass(frozen=True)
class CacheKey:
    endpoint: str
    uuid: str


@dataclass
class CacheEntry:
    payload: JsonPayload
    fetched_at: float


@dataclass
class CacheRequest:
    key: CacheKey
    fetcher: Callable[[], JsonPayload]
    event: threading.Event = field(default_factory=threading.Event)
    error: Exception | None = None


CACHE: dict[str, dict[str, CacheEntry]] = {}
CACHE_LOCK = threading.RLock()
IN_FLIGHT: dict[tuple[str, str], CacheRequest] = {}
FETCH_QUEUE: queue.Queue[CacheRequest] = queue.Queue()
WORKER_THREAD: threading.Thread | None = None


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
    except ValueError:
        return False
    return True


def _sanitize_segment(segment: str) -> str:
    sanitized = segment.strip().replace("/", "_")
    if not sanitized:
        raise RuntimeError("Cache endpoint segment must not be empty")
    return sanitized


def build_cache_key(endpoint: str) -> CacheKey:
    parsed_endpoint = urlparse(endpoint.strip())
    normalized = parsed_endpoint.path.strip("/")
    if not normalized:
        raise RuntimeError("Endpoint must not be empty")

    segments = [segment for segment in normalized.split("/") if segment]
    query_items = parse_qsl(parsed_endpoint.query, keep_blank_values=True)
    query_key = None
    if query_items:
        query_key = "__".join(
            f"{_sanitize_segment(key)}={_sanitize_segment(value)}"
            for key, value in sorted(query_items)
        )

    if len(segments) == 1:
        return CacheKey(
            endpoint=_sanitize_segment(segments[0]),
            uuid=COLLECTION_CACHE_KEY if query_key is None else query_key,
        )

    if len(segments) >= 2 and _is_uuid(segments[1]):
        endpoint_segments = [segments[0], *segments[2:]]
        endpoint_name = "__".join(_sanitize_segment(segment) for segment in endpoint_segments)
        uuid_key = segments[1] if query_key is None else f"{segments[1]}__{query_key}"
        return CacheKey(endpoint=endpoint_name, uuid=uuid_key)

    raise RuntimeError(f"Endpoint does not match the supported cache key pattern: {endpoint!r}")


def _cache_file_path(key: CacheKey) -> Path:
    return CACHE_DIR / key.endpoint / f"{key.uuid}.json"


def _load_persisted_cache() -> None:
    CACHE_DIR.mkdir(exist_ok=True)

    for endpoint_dir in CACHE_DIR.iterdir():
        if not endpoint_dir.is_dir():
            continue

        endpoint_name = endpoint_dir.name
        for cache_file in endpoint_dir.glob("*.json"):
            try:
                payload = json.loads(cache_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                LOGGER.warning("Skipping invalid cache file: %s", cache_file)
                continue

            if not isinstance(payload, (dict, list)):
                LOGGER.warning("Skipping non-JSON cache file: %s", cache_file)
                continue

            cache_key = cache_file.stem
            with CACHE_LOCK:
                CACHE.setdefault(endpoint_name, {})[cache_key] = CacheEntry(
                    payload=payload,
                    fetched_at=cache_file.stat().st_mtime,
                )

    LOGGER.info("Loaded cache index with %s endpoint groups", len(CACHE))


def _persist_entry(key: CacheKey, payload: JsonPayload) -> None:
    cache_file = _cache_file_path(key)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(payload), encoding="utf-8")


def _store_entry(key: CacheKey, payload: JsonPayload) -> JsonPayload:
    now = time.time()
    _persist_entry(key, payload)

    with CACHE_LOCK:
        CACHE.setdefault(key.endpoint, {})[key.uuid] = CacheEntry(
            payload=payload,
            fetched_at=now,
        )

    LOGGER.info("Stored cache item endpoint=%s uuid=%s", key.endpoint, key.uuid)
    return payload


def _get_cached_entry(key: CacheKey, cache_duration_seconds: float) -> CacheEntry | None:
    with CACHE_LOCK:
        endpoint_entries = CACHE.get(key.endpoint)
        if endpoint_entries is None:
            return None

        entry = endpoint_entries.get(key.uuid)
        if entry is None:
            return None

        if time.time() - entry.fetched_at > cache_duration_seconds:
            return None

        return entry


def _cache_worker() -> None:
    while True:
        request = FETCH_QUEUE.get()
        inflight_key = (request.key.endpoint, request.key.uuid)

        try:
            LOGGER.info(
                "Fetching cache miss endpoint=%s uuid=%s",
                request.key.endpoint,
                request.key.uuid,
            )
            payload = request.fetcher()
            if not isinstance(payload, (dict, list)):
                raise RuntimeError(
                    f"Expected a JSON object or list payload for endpoint={request.key.endpoint} uuid={request.key.uuid}"
                )
            _store_entry(request.key, payload)
        except Exception as exc:
            request.error = exc
            LOGGER.exception(
                "Cache fetch failed endpoint=%s uuid=%s",
                request.key.endpoint,
                request.key.uuid,
            )
        finally:
            with CACHE_LOCK:
                IN_FLIGHT.pop(inflight_key, None)
            request.event.set()
            FETCH_QUEUE.task_done()


def _ensure_worker_thread() -> None:
    global WORKER_THREAD

    with CACHE_LOCK:
        if WORKER_THREAD is not None and WORKER_THREAD.is_alive():
            return

        WORKER_THREAD = threading.Thread(
            target=_cache_worker,
            name="endpoint-cache-worker",
            daemon=True,
        )
        WORKER_THREAD.start()
        LOGGER.info("Started endpoint cache worker thread")


def get_cached_json(
    endpoint: str,
    fetcher: Callable[[], JsonPayload],
    cache_duration_seconds: float,
) -> tuple[JsonPayload, bool]:
    key = build_cache_key(endpoint)
    cached_entry = _get_cached_entry(key, cache_duration_seconds)
    if cached_entry is not None:
        LOGGER.debug("Cache hit endpoint=%s uuid=%s", key.endpoint, key.uuid)
        return cached_entry.payload, True

    _ensure_worker_thread()

    with CACHE_LOCK:
        cached_entry = _get_cached_entry(key, cache_duration_seconds)
        if cached_entry is not None:
            LOGGER.debug("Cache hit after lock endpoint=%s uuid=%s", key.endpoint, key.uuid)
            return cached_entry.payload, True

        inflight_key = (key.endpoint, key.uuid)
        request = IN_FLIGHT.get(inflight_key)
        if request is None:
            request = CacheRequest(key=key, fetcher=fetcher)
            IN_FLIGHT[inflight_key] = request
            FETCH_QUEUE.put(request)
            LOGGER.info("Queued cache fetch endpoint=%s uuid=%s", key.endpoint, key.uuid)
        else:
            LOGGER.info(
                "Waiting for in-flight cache fetch endpoint=%s uuid=%s",
                key.endpoint,
                key.uuid,
            )

    request.event.wait()
    if request.error is not None:
        raise request.error

    cached_entry = _get_cached_entry(key, cache_duration_seconds)
    if cached_entry is None:
        raise RuntimeError(
            f"Cache fetch completed without a stored payload for endpoint={key.endpoint} uuid={key.uuid}"
        )

    return cached_entry.payload, False


def get_cache_snapshot() -> dict[str, dict[str, dict]]:
    with CACHE_LOCK:
        return {
            endpoint: {
                uuid: {
                    "payload": entry.payload,
                    "fetched_at": entry.fetched_at,
                }
                for uuid, entry in entries.items()
            }
            for endpoint, entries in CACHE.items()
        }


_load_persisted_cache()
