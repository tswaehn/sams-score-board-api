from __future__ import annotations

import json
import logging
import queue
import threading
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qsl, urlparse
from uuid import UUID


LOGGER = logging.getLogger("competition-api.cache")
COLLECTION_CACHE_KEY = "_collection"
CACHE_DIR = Path(__file__).with_name("cache")
CURRENT_SEASON_TTL_SECONDS = 60
NON_CURRENT_SEASON_TTL_SECONDS = 28 * 24 * 60 * 60
JsonPayload = dict | list


@dataclass(frozen=True)
class CacheKey:
    endpoint: str
    uuid: str


@dataclass(frozen=True)
class CachedObject:
    current_season: bool | None = None

    TYPE = "cached-object"

    def cache_key(self) -> CacheKey:
        raise NotImplementedError

    def cache_ttl_seconds(self) -> float:
        if self.current_season is False:
            return NON_CURRENT_SEASON_TTL_SECONDS
        return CURRENT_SEASON_TTL_SECONDS

    def infer_current_season(self, payload: JsonPayload) -> bool | None:
        return self.current_season

    def resolved(self, payload: JsonPayload) -> "CachedObject":
        inferred_current_season = self.infer_current_season(payload)
        if inferred_current_season is None or inferred_current_season == self.current_season:
            return self
        return replace(self, current_season=inferred_current_season)

    def to_meta(self) -> dict[str, str | bool | None]:
        return {
            "type": self.TYPE,
            "currentSeason": self.current_season,
        }


@dataclass(frozen=True)
class CompetitionListCachedObject(CachedObject):
    season_uuid: str | None = None
    TYPE = "competition-list"

    def cache_key(self) -> CacheKey:
        return CacheKey(
            endpoint="competitions",
            uuid=COLLECTION_CACHE_KEY if self.season_uuid is None else f"season={self.season_uuid}",
        )


@dataclass(frozen=True)
class CompetitionCachedObject(CachedObject):
    competition_uuid: str = ""
    TYPE = "competition"

    def cache_key(self) -> CacheKey:
        return CacheKey(endpoint="competitions", uuid=self.competition_uuid)


@dataclass(frozen=True)
class SeasonCachedObject(CachedObject):
    season_uuid: str | None = None
    TYPE = "season"

    def cache_key(self) -> CacheKey:
        return CacheKey(
            endpoint="seasons",
            uuid=COLLECTION_CACHE_KEY if self.season_uuid is None else self.season_uuid,
        )

    def infer_current_season(self, payload: JsonPayload) -> bool | None:
        if isinstance(payload, dict):
            current_season = payload.get("currentSeason")
            if isinstance(current_season, bool):
                return current_season
            return None

        return any(bool(season.get("currentSeason")) for season in payload if isinstance(season, dict))


@dataclass(frozen=True)
class AssociationCachedObject(CachedObject):
    association_uuid: str = ""
    TYPE = "association"

    def cache_key(self) -> CacheKey:
        return CacheKey(endpoint="associations", uuid=self.association_uuid)


@dataclass(frozen=True)
class TeamsCachedObject(CachedObject):
    competition_uuid: str = ""
    TYPE = "teams"

    def cache_key(self) -> CacheKey:
        return CacheKey(endpoint="competitions__teams", uuid=self.competition_uuid)


@dataclass(frozen=True)
class RankingsCachedObject(CachedObject):
    competition_uuid: str = ""
    TYPE = "rankings"

    def cache_key(self) -> CacheKey:
        return CacheKey(endpoint="competitions__rankings", uuid=self.competition_uuid)


@dataclass(frozen=True)
class MatchGroupsCachedObject(CachedObject):
    competition_uuid: str = ""
    TYPE = "match-groups"

    def cache_key(self) -> CacheKey:
        return CacheKey(endpoint="competitions__match-groups", uuid=self.competition_uuid)


@dataclass(frozen=True)
class CompetitionMatchesCachedObject(CachedObject):
    match_group_uuid: str = ""
    TYPE = "competition-matches"

    def cache_key(self) -> CacheKey:
        return CacheKey(endpoint="match-groups__competition-matches", uuid=self.match_group_uuid)


@dataclass
class CacheEntry:
    payload: JsonPayload
    fetched_at: float
    cached_object: CachedObject


@dataclass
class CacheRequest:
    cached_object: CachedObject
    fetcher: Callable[[], JsonPayload | tuple[JsonPayload, CachedObject]]
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


def _query_items(parsed_endpoint) -> list[tuple[str, str]]:
    return parse_qsl(parsed_endpoint.query, keep_blank_values=True)


def _single_query_value(query_items: list[tuple[str, str]], key: str) -> str | None:
    values = [value for item_key, value in query_items if item_key == key]
    if len(values) != 1:
        return None
    return values[0]


def build_cache_key(endpoint: str) -> CacheKey:
    return cached_object_from_endpoint(endpoint).cache_key()


def cached_object_from_endpoint(
    endpoint: str,
    *,
    current_season: bool | None = None,
) -> CachedObject:
    parsed_endpoint = urlparse(endpoint.strip())
    normalized = parsed_endpoint.path.strip("/")
    if not normalized:
        raise RuntimeError("Endpoint must not be empty")

    segments = [segment for segment in normalized.split("/") if segment]
    query_items = _query_items(parsed_endpoint)

    if len(segments) == 1:
        resource = segments[0]
        if resource == "seasons":
            return SeasonCachedObject(current_season=current_season)
        if resource == "competitions":
            season_uuid = _single_query_value(query_items, "season")
            return CompetitionListCachedObject(
                current_season=current_season,
                season_uuid=season_uuid,
            )

    if len(segments) >= 2 and _is_uuid(segments[1]):
        resource = segments[0]
        resource_uuid = segments[1]
        suffix = segments[2:]

        if resource == "competitions" and not suffix:
            return CompetitionCachedObject(
                current_season=current_season,
                competition_uuid=resource_uuid,
            )
        if resource == "competitions" and suffix == ["teams"]:
            return TeamsCachedObject(
                current_season=current_season,
                competition_uuid=resource_uuid,
            )
        if resource == "competitions" and suffix == ["rankings"]:
            return RankingsCachedObject(
                current_season=current_season,
                competition_uuid=resource_uuid,
            )
        if resource == "competitions" and suffix == ["match-groups"]:
            return MatchGroupsCachedObject(
                current_season=current_season,
                competition_uuid=resource_uuid,
            )
        if resource == "match-groups" and suffix == ["competition-matches"]:
            return CompetitionMatchesCachedObject(
                current_season=current_season,
                match_group_uuid=resource_uuid,
            )
        if resource == "seasons" and not suffix:
            return SeasonCachedObject(
                current_season=current_season,
                season_uuid=resource_uuid,
            )
        if resource == "associations" and not suffix:
            return AssociationCachedObject(
                current_season=current_season,
                association_uuid=resource_uuid,
            )

    raise RuntimeError(f"Endpoint does not match a supported cached object pattern: {endpoint!r}")


def _cache_file_path(key: CacheKey) -> Path:
    return CACHE_DIR / key.endpoint / f"{key.uuid}.json"


def _cached_object_from_meta(key: CacheKey, meta: dict | None, payload: JsonPayload) -> CachedObject:
    current_season = None
    if isinstance(meta, dict):
        current_season_value = meta.get("currentSeason")
        if isinstance(current_season_value, bool):
            current_season = current_season_value

    endpoint = key.endpoint
    uuid_key = key.uuid

    if endpoint == "competitions" and uuid_key == COLLECTION_CACHE_KEY:
        return CompetitionListCachedObject(current_season=current_season)
    if endpoint == "competitions" and uuid_key.startswith("season="):
        return CompetitionListCachedObject(
            current_season=current_season,
            season_uuid=uuid_key.removeprefix("season="),
        )
    if endpoint == "competitions":
        return CompetitionCachedObject(current_season=current_season, competition_uuid=uuid_key)
    if endpoint == "seasons" and uuid_key == COLLECTION_CACHE_KEY:
        return SeasonCachedObject(current_season=current_season).resolved(payload)
    if endpoint == "seasons":
        return SeasonCachedObject(current_season=current_season, season_uuid=uuid_key).resolved(payload)
    if endpoint == "associations":
        return AssociationCachedObject(current_season=current_season, association_uuid=uuid_key)
    if endpoint == "competitions__teams":
        return TeamsCachedObject(current_season=current_season, competition_uuid=uuid_key)
    if endpoint == "competitions__rankings":
        return RankingsCachedObject(current_season=current_season, competition_uuid=uuid_key)
    if endpoint == "competitions__match-groups":
        return MatchGroupsCachedObject(current_season=current_season, competition_uuid=uuid_key)
    if endpoint == "match-groups__competition-matches":
        return CompetitionMatchesCachedObject(current_season=current_season, match_group_uuid=uuid_key)

    return cached_object_from_endpoint(
        "/" + endpoint.replace("__", "/") + ("" if uuid_key == COLLECTION_CACHE_KEY else f"/{uuid_key}"),
        current_season=current_season,
    ).resolved(payload)


def _load_persisted_cache() -> None:
    CACHE_DIR.mkdir(exist_ok=True)

    for endpoint_dir in CACHE_DIR.iterdir():
        if not endpoint_dir.is_dir():
            continue

        endpoint_name = endpoint_dir.name
        for cache_file in endpoint_dir.glob("*.json"):
            try:
                raw_payload = json.loads(cache_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                LOGGER.warning("Skipping invalid cache file: %s", cache_file)
                continue

            payload: JsonPayload
            meta: dict | None = None
            if (
                isinstance(raw_payload, dict)
                and isinstance(raw_payload.get("_cache_meta"), dict)
                and isinstance(raw_payload.get("payload"), (dict, list))
            ):
                payload = raw_payload["payload"]
                meta = raw_payload["_cache_meta"]
            elif isinstance(raw_payload, (dict, list)):
                payload = raw_payload
            else:
                LOGGER.warning("Skipping non-JSON cache file: %s", cache_file)
                continue

            key = CacheKey(endpoint=endpoint_name, uuid=cache_file.stem)
            cached_object = _cached_object_from_meta(key, meta, payload)

            with CACHE_LOCK:
                CACHE.setdefault(endpoint_name, {})[cache_file.stem] = CacheEntry(
                    payload=payload,
                    fetched_at=cache_file.stat().st_mtime,
                    cached_object=cached_object,
                )

    LOGGER.info("Loaded cache index with %s endpoint groups", len(CACHE))


def _persist_entry(entry: CacheEntry) -> None:
    cache_file = _cache_file_path(entry.cached_object.cache_key())
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(
        json.dumps(
            {
                "_cache_meta": entry.cached_object.to_meta(),
                "payload": entry.payload,
            }
        ),
        encoding="utf-8",
    )


def _store_entry(cached_object: CachedObject, payload: JsonPayload) -> JsonPayload:
    entry = CacheEntry(
        payload=payload,
        fetched_at=time.time(),
        cached_object=cached_object,
    )
    _persist_entry(entry)

    key = cached_object.cache_key()
    with CACHE_LOCK:
        CACHE.setdefault(key.endpoint, {})[key.uuid] = entry

    LOGGER.info(
        "Stored cache item endpoint=%s uuid=%s type=%s current_season=%s",
        key.endpoint,
        key.uuid,
        cached_object.TYPE,
        cached_object.current_season,
    )
    return payload


def _get_cached_entry(requested_object: CachedObject) -> CacheEntry | None:
    key = requested_object.cache_key()

    with CACHE_LOCK:
        endpoint_entries = CACHE.get(key.endpoint)
        if endpoint_entries is None:
            return None

        entry = endpoint_entries.get(key.uuid)
        if entry is None:
            return None

        ttl_source = entry.cached_object
        if requested_object.current_season is not None:
            ttl_source = replace(entry.cached_object, current_season=requested_object.current_season)

        if time.time() - entry.fetched_at > ttl_source.cache_ttl_seconds():
            return None

        return entry


def _normalize_fetch_result(
    requested_object: CachedObject,
    fetch_result: JsonPayload | tuple[JsonPayload, CachedObject],
) -> tuple[JsonPayload, CachedObject]:
    if isinstance(fetch_result, tuple):
        payload, resolved_object = fetch_result
    else:
        payload = fetch_result
        resolved_object = requested_object.resolved(payload)

    if not isinstance(payload, (dict, list)):
        raise RuntimeError(
            f"Expected a JSON object or list payload for endpoint={requested_object.cache_key().endpoint} "
            f"uuid={requested_object.cache_key().uuid}"
        )

    return payload, resolved_object


def _cache_worker() -> None:
    while True:
        request = FETCH_QUEUE.get()
        key = request.cached_object.cache_key()
        inflight_key = (key.endpoint, key.uuid)

        try:
            LOGGER.info(
                "Fetching cache miss endpoint=%s uuid=%s type=%s current_season=%s",
                key.endpoint,
                key.uuid,
                request.cached_object.TYPE,
                request.cached_object.current_season,
            )
            payload, resolved_object = _normalize_fetch_result(request.cached_object, request.fetcher())
            _store_entry(resolved_object, payload)
        except Exception as exc:
            request.error = exc
            LOGGER.exception(
                "Cache fetch failed endpoint=%s uuid=%s",
                key.endpoint,
                key.uuid,
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
    cached_object: CachedObject,
    fetcher: Callable[[], JsonPayload | tuple[JsonPayload, CachedObject]],
) -> tuple[JsonPayload, bool]:
    key = cached_object.cache_key()
    cached_entry = _get_cached_entry(cached_object)
    if cached_entry is not None:
        LOGGER.debug("Cache hit endpoint=%s uuid=%s", key.endpoint, key.uuid)
        return cached_entry.payload, True

    _ensure_worker_thread()

    with CACHE_LOCK:
        cached_entry = _get_cached_entry(cached_object)
        if cached_entry is not None:
            LOGGER.debug("Cache hit after lock endpoint=%s uuid=%s", key.endpoint, key.uuid)
            return cached_entry.payload, True

        inflight_key = (key.endpoint, key.uuid)
        request = IN_FLIGHT.get(inflight_key)
        if request is None:
            request = CacheRequest(cached_object=cached_object, fetcher=fetcher)
            IN_FLIGHT[inflight_key] = request
            FETCH_QUEUE.put(request)
            LOGGER.info(
                "Queued cache fetch endpoint=%s uuid=%s type=%s current_season=%s",
                key.endpoint,
                key.uuid,
                cached_object.TYPE,
                cached_object.current_season,
            )
        else:
            LOGGER.info(
                "Waiting for in-flight cache fetch endpoint=%s uuid=%s",
                key.endpoint,
                key.uuid,
            )

    request.event.wait()
    if request.error is not None:
        raise request.error

    cached_entry = _get_cached_entry(cached_object)
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
                    "type": entry.cached_object.TYPE,
                    "currentSeason": entry.cached_object.current_season,
                }
                for uuid, entry in entries.items()
            }
            for endpoint, entries in CACHE.items()
        }


_load_persisted_cache()
