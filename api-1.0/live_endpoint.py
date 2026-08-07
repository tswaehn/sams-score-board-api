from __future__ import annotations

import json
import logging
import threading
import time
from copy import deepcopy
from urllib.parse import urlparse

import requests
from requests import RequestException
from websocket import WebSocketConnectionClosedException, WebSocketTimeoutException, create_connection
from server_config import LIVE_API_SNAPSHOT_REFRESH_SECONDS, LIVE_API_URLS


LOGGER = logging.getLogger("api.live")

LIVE_API_TIMEOUT_SECONDS = 30
LIVE_API_WS_TIMEOUT_SECONDS = 55
LIVE_API_WS_RECONNECT_SECONDS = 3
LIVE_API_SNAPSHOT_REFRESH_SECONDS = max(1, LIVE_API_SNAPSHOT_REFRESH_SECONDS)
LIVE_API_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Connection": "close",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.0 Safari/537.36"
    ),
}


def _get_live_api_urls() -> list[str]:
    return list(LIVE_API_URLS)


def _parse_live_api_url(live_api_url: str | None) -> tuple[str, str, str]:
    if not live_api_url:
        raise RuntimeError("Missing live_api_urls in server config")

    parsed_url = urlparse(live_api_url)
    path_segments = [segment for segment in parsed_url.path.split("/") if segment]
    if len(path_segments) != 4 or path_segments[0] != "live" or path_segments[2] != "tickers":
        raise RuntimeError(
            "Live API URL must match /live/<ticker_type>/tickers/<ticker_id>"
        )

    ticker_type = path_segments[1]
    ticker_id = path_segments[3]
    if not ticker_type or not ticker_id:
        raise RuntimeError(
            "Live API URL must contain both ticker type and ticker id"
        )

    if not parsed_url.netloc:
        raise RuntimeError("Live API URL must include a hostname")

    return ticker_type, ticker_id, f"wss://{parsed_url.netloc}/{ticker_type}/{ticker_id}"


class LiveStateUpdater:
    def __init__(self, live_api_url: str | None) -> None:
        self._live_api_url = live_api_url
        self._lock = threading.RLock()
        self._payload: dict = {}
        self._version = 0
        self._competition_payload_cache: dict[str, tuple[int, dict]] = {}
        self._error: str | None = None
        self._thread: threading.Thread | None = None
        self._ticker_type: str | None = None
        self._ticker_id: str | None = None
        self._ws_url: str | None = None

    def start(self) -> None:
        with self._lock:
            if self._ws_url is None:
                self._ticker_type, self._ticker_id, self._ws_url = self._parse_config()

            if self._thread is not None and self._thread.is_alive():
                return

            self._thread = threading.Thread(
                target=self._run,
                name="live-api-websocket",
                daemon=True,
            )
            self._thread.start()

    def get_payload(self) -> dict:
        with self._lock:
            return deepcopy(self._payload)

    def get_competition_payload(self, competition_uuid: str) -> dict:
        with self._lock:
            if not self._payload:
                return {}

            cached_entry = self._competition_payload_cache.get(competition_uuid)
            if cached_entry is not None:
                cached_version, cached_payload = cached_entry
                if cached_version == self._version:
                    return deepcopy(cached_payload)

            filtered_payload = self._filter_payload(self._payload, competition_uuid)
            self._competition_payload_cache[competition_uuid] = (self._version, filtered_payload)
            return deepcopy(filtered_payload)

    def _parse_config(self) -> tuple[str, str, str]:
        return _parse_live_api_url(self._live_api_url)

    def _fetch_snapshot(self) -> dict:
        response = requests.get(
            self._live_api_url,
            headers=LIVE_API_HEADERS,
            timeout=LIVE_API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError(
                f"Expected a dict payload from configured live API URL, got {type(payload).__name__}"
            )

        return payload

    def _store_snapshot(self, payload: dict) -> None:
        with self._lock:
            self._payload = payload
            self._version += 1
            self._competition_payload_cache.clear()
            self._error = None

    def _set_error(self, message: str) -> None:
        with self._lock:
            self._error = message

    def _merge_message(self, message: dict) -> None:
        message_type = message.get("type")
        message_payload = message.get("payload")

        with self._lock:
            if message_type == "FETCH_DATA_RESPONSE_ERROR":
                payload_type = message_payload.get("type") if isinstance(message_payload, dict) else None
                self._error = f"Live websocket reported an error: {payload_type or 'unknown'}"
                return

            if not isinstance(message_payload, dict):
                return

            if message_type == "MATCH_UPDATE":
                match_uuid = message_payload.get("matchUuid")
                if isinstance(match_uuid, str):
                    match_states = self._payload.setdefault("matchStates", {})
                    if isinstance(match_states, dict):
                        match_states[match_uuid] = message_payload
                        self._version += 1
                        self._competition_payload_cache.clear()
                return

            if message_type == "MATCH_STATS_UPDATE":
                match_uuid = message_payload.get("matchUuid")
                if isinstance(match_uuid, str):
                    match_stats = self._payload.setdefault("matchStats", {})
                    if isinstance(match_stats, dict):
                        match_stats[match_uuid] = message_payload
                        self._version += 1
                        self._competition_payload_cache.clear()

    def _refresh_snapshot_if_due(self, next_refresh_at: float) -> float:
        if time.monotonic() < next_refresh_at:
            return next_refresh_at

        self._store_snapshot(self._fetch_snapshot())
        return time.monotonic() + LIVE_API_SNAPSHOT_REFRESH_SECONDS

    def _run(self) -> None:
        if self._ws_url is None or self._ticker_type is None or self._ticker_id is None:
            raise RuntimeError("Live state updater was started without valid websocket config")

        ws_timeout_seconds = min(
            LIVE_API_WS_TIMEOUT_SECONDS,
            LIVE_API_SNAPSHOT_REFRESH_SECONDS,
        )

        while True:
            ws = None
            try:
                self._store_snapshot(self._fetch_snapshot())
                next_snapshot_refresh_at = time.monotonic() + LIVE_API_SNAPSHOT_REFRESH_SECONDS
                ws = create_connection(self._ws_url, timeout=ws_timeout_seconds)
                LOGGER.info(
                    "Connected live websocket: %s (%s/%s)",
                    self._ws_url,
                    self._ticker_type,
                    self._ticker_id,
                )

                while True:
                    next_snapshot_refresh_at = self._refresh_snapshot_if_due(
                        next_snapshot_refresh_at
                    )

                    try:
                        raw_message = ws.recv()
                    except WebSocketTimeoutException:
                        next_snapshot_refresh_at = self._refresh_snapshot_if_due(
                            next_snapshot_refresh_at
                        )
                        continue

                    if not raw_message:
                        raise WebSocketConnectionClosedException("Live websocket closed")

                    message = json.loads(raw_message)
                    if not isinstance(message, dict):
                        continue

                    self._merge_message(message)
                    next_snapshot_refresh_at = self._refresh_snapshot_if_due(
                        next_snapshot_refresh_at
                    )
            except RequestException as exc:
                self._set_error("Failed to fetch live data")
                LOGGER.warning("Live snapshot fetch failed: %s", exc)
            except (
                RuntimeError,
                ValueError,
                WebSocketConnectionClosedException,
                WebSocketTimeoutException,
            ) as exc:
                self._set_error("Live websocket disconnected")
                LOGGER.warning("Live websocket loop failed: %s", exc)
            except Exception:
                self._set_error("Live websocket disconnected")
                LOGGER.exception("Unexpected live websocket error")
            finally:
                if ws is not None:
                    try:
                        ws.close()
                    except Exception:
                        pass

            time.sleep(LIVE_API_WS_RECONNECT_SECONDS)

    @staticmethod
    def _filter_payload(payload: dict, competition_uuid: str) -> dict:
        match_days = payload.get("matchDays")
        if not isinstance(match_days, list):
            return {}

        filtered_match_days = []
        included_match_ids: set[str] = set()

        for match_day in match_days:
            if not isinstance(match_day, dict):
                continue

            matches = match_day.get("matches")
            if not isinstance(matches, list):
                continue

            filtered_matches = []
            for match in matches:
                if not isinstance(match, dict):
                    continue
                if match.get("matchSeries") != competition_uuid:
                    continue

                filtered_match = deepcopy(match)
                filtered_matches.append(filtered_match)

                match_id = filtered_match.get("id")
                if isinstance(match_id, str):
                    included_match_ids.add(match_id)

            if not filtered_matches:
                continue

            filtered_match_day = deepcopy(match_day)
            filtered_match_day["matches"] = filtered_matches
            filtered_match_days.append(filtered_match_day)

        filtered_payload = dict(payload)
        filtered_payload["matchDays"] = filtered_match_days

        match_series = payload.get("matchSeries")
        if isinstance(match_series, dict):
            filtered_payload["matchSeries"] = (
                {competition_uuid: deepcopy(match_series[competition_uuid])}
                if competition_uuid in match_series
                else {}
            )

        for key in ("matchStates", "matchStats"):
            value = payload.get(key)
            if isinstance(value, dict):
                filtered_payload[key] = {
                    match_id: deepcopy(match_value)
                    for match_id, match_value in value.items()
                    if match_id in included_match_ids
                }

        return filtered_payload


class MultiLiveStateUpdater:
    def __init__(self, live_api_urls: list[str]) -> None:
        self._updaters = [LiveStateUpdater(live_api_url) for live_api_url in live_api_urls]

    def start(self) -> None:
        for updater in self._updaters:
            updater.start()

    def get_payload(self) -> dict:
        payloads = [updater.get_payload() for updater in self._updaters]
        return self._merge_payloads(payloads)

    def get_competition_payload(self, competition_uuid: str) -> dict:
        payloads = [updater.get_competition_payload(competition_uuid) for updater in self._updaters]
        return self._merge_payloads(payloads)

    def _merge_payloads(self, payloads: list[dict]) -> dict:
        merged_payload: dict = {}
        merged_match_days: list = []
        merged_dict_sections = {
            "matchSeries": {},
            "matchStates": {},
            "matchStats": {},
        }

        for payload in payloads:
            if not isinstance(payload, dict) or not payload:
                continue

            match_days = payload.get("matchDays")
            if isinstance(match_days, list):
                merged_match_days.extend(deepcopy(match_days))

            for key, merged_section in merged_dict_sections.items():
                value = payload.get(key)
                if isinstance(value, dict):
                    merged_section.update(deepcopy(value))

            settings = payload.get("settings")
            if "settings" not in merged_payload and isinstance(settings, dict):
                merged_payload["settings"] = deepcopy(settings)

        if merged_match_days:
            merged_payload["matchDays"] = merged_match_days

        for key, merged_section in merged_dict_sections.items():
            merged_payload[key] = merged_section

        return merged_payload


LIVE_STATE_UPDATER = MultiLiveStateUpdater(_get_live_api_urls())


def startup_live_endpoint() -> None:
    if not _get_live_api_urls():
        raise RuntimeError("live_api_urls is required to start the live endpoint")

    LIVE_STATE_UPDATER.start()


def get_live_payload(competition_uuid: str | None = None) -> dict:
    if competition_uuid is None:
        return LIVE_STATE_UPDATER.get_payload()

    return LIVE_STATE_UPDATER.get_competition_payload(competition_uuid)
