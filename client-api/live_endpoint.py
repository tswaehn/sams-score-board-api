from __future__ import annotations

import json
import logging
import os
import threading
import time
from copy import deepcopy
from urllib.parse import urlparse

import requests
from requests import RequestException
from websocket import WebSocketConnectionClosedException, WebSocketTimeoutException, create_connection


LOGGER = logging.getLogger("competition-api.live")

LIVE_API_URL = os.getenv("LIVE_API_URL")
LIVE_API_TIMEOUT_SECONDS = 30
LIVE_API_WS_TIMEOUT_SECONDS = 55
LIVE_API_WS_RECONNECT_SECONDS = 3
LIVE_API_FILTER_CACHE_TTL_SECONDS = 2
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
LIVE_API_STATE_LOCK = threading.RLock()
LIVE_API_STATE_PAYLOAD: dict | None = None
LIVE_API_STATE_ERROR: str | None = None
LIVE_API_WS_THREAD: threading.Thread | None = None
LIVE_API_FILTER_CACHE: dict[str, tuple[float, dict]] = {}


def parse_live_api_config() -> tuple[str, str]:
    if not LIVE_API_URL:
        raise RuntimeError("Missing environment variable: LIVE_API_URL")

    parsed_url = urlparse(LIVE_API_URL)
    path_segments = [segment for segment in parsed_url.path.split("/") if segment]
    if len(path_segments) != 4 or path_segments[0] != "live" or path_segments[2] != "tickers":
        raise RuntimeError(
            "LIVE_API_URL must match /live/<ticker_type>/tickers/<ticker_id>"
        )

    ticker_type = path_segments[1]
    ticker_id = path_segments[3]
    if not ticker_type or not ticker_id:
        raise RuntimeError(
            "LIVE_API_URL must contain both ticker type and ticker id"
        )

    return ticker_type, ticker_id


def build_live_ws_url() -> str:
    parsed_url = urlparse(LIVE_API_URL or "")
    ticker_type, ticker_id = parse_live_api_config()
    if not parsed_url.netloc:
        raise RuntimeError("LIVE_API_URL must include a hostname")

    return f"wss://{parsed_url.netloc}/{ticker_type}/{ticker_id}"


def fetch_live_snapshot() -> dict:
    response = requests.get(
        LIVE_API_URL,
        headers=LIVE_API_HEADERS,
        timeout=LIVE_API_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"Expected a dict payload from LIVE_API_URL, got {type(payload).__name__}"
        )

    return payload


def filter_live_payload(payload: dict, competition_uuid: str | None = None) -> dict:
    if competition_uuid is None:
        return payload

    now = time.monotonic()
    with LIVE_API_STATE_LOCK:
        cached_entry = LIVE_API_FILTER_CACHE.get(competition_uuid)
        if cached_entry is not None:
            expires_at, cached_payload = cached_entry
            if expires_at > now:
                return cached_payload

    match_days = payload.get("matchDays")
    if not isinstance(match_days, list):
        raise RuntimeError("Live payload is missing a valid matchDays list")

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

    with LIVE_API_STATE_LOCK:
        LIVE_API_FILTER_CACHE[competition_uuid] = (
            now + LIVE_API_FILTER_CACHE_TTL_SECONDS,
            filtered_payload,
        )

    return filtered_payload


def store_live_payload(payload: dict) -> None:
    global LIVE_API_STATE_PAYLOAD, LIVE_API_STATE_ERROR, LIVE_API_FILTER_CACHE

    with LIVE_API_STATE_LOCK:
        LIVE_API_STATE_PAYLOAD = payload
        LIVE_API_STATE_ERROR = None
        LIVE_API_FILTER_CACHE = {}


def merge_live_message(message: dict) -> None:
    global LIVE_API_STATE_ERROR

    message_type = message.get("type")
    message_payload = message.get("payload")

    with LIVE_API_STATE_LOCK:
        if message_type == "FETCH_DATA_RESPONSE_ERROR":
            payload_type = message_payload.get("type") if isinstance(message_payload, dict) else None
            LIVE_API_STATE_ERROR = (
                f"Live websocket reported an error: {payload_type or 'unknown'}"
            )
            return

        if not isinstance(LIVE_API_STATE_PAYLOAD, dict):
            return

        if message_type == "MATCH_UPDATE" and isinstance(message_payload, dict):
            match_uuid = message_payload.get("matchUuid")
            if isinstance(match_uuid, str):
                match_states = LIVE_API_STATE_PAYLOAD.setdefault("matchStates", {})
                if isinstance(match_states, dict):
                    match_states[match_uuid] = message_payload
            return

        if message_type == "MATCH_STATS_UPDATE" and isinstance(message_payload, dict):
            match_uuid = message_payload.get("matchUuid")
            if isinstance(match_uuid, str):
                match_stats = LIVE_API_STATE_PAYLOAD.setdefault("matchStats", {})
                if isinstance(match_stats, dict):
                    match_stats[match_uuid] = message_payload


def live_ws_worker() -> None:
    global LIVE_API_STATE_ERROR

    ws_url = build_live_ws_url()

    while True:
        ws = None
        try:
            store_live_payload(fetch_live_snapshot())
            ws = create_connection(ws_url, timeout=LIVE_API_WS_TIMEOUT_SECONDS)
            LOGGER.info("Connected live websocket: %s", ws_url)

            while True:
                raw_message = ws.recv()
                if not raw_message:
                    raise WebSocketConnectionClosedException("Live websocket closed")

                message = json.loads(raw_message)
                if not isinstance(message, dict):
                    continue

                merge_live_message(message)
        except RequestException as exc:
            with LIVE_API_STATE_LOCK:
                LIVE_API_STATE_ERROR = "Failed to fetch live data"
            LOGGER.warning("Live snapshot fetch failed: %s", exc)
        except (
            RuntimeError,
            ValueError,
            WebSocketConnectionClosedException,
            WebSocketTimeoutException,
        ) as exc:
            with LIVE_API_STATE_LOCK:
                LIVE_API_STATE_ERROR = "Live websocket disconnected"
            LOGGER.warning("Live websocket loop failed: %s", exc)
        except Exception:
            with LIVE_API_STATE_LOCK:
                LIVE_API_STATE_ERROR = "Live websocket disconnected"
            LOGGER.exception("Unexpected live websocket error")
        finally:
            if ws is not None:
                try:
                    ws.close()
                except Exception:
                    pass

        time.sleep(LIVE_API_WS_RECONNECT_SECONDS)


def ensure_live_ws_worker() -> None:
    global LIVE_API_WS_THREAD

    with LIVE_API_STATE_LOCK:
        if LIVE_API_WS_THREAD is not None and LIVE_API_WS_THREAD.is_alive():
            return

        LIVE_API_WS_THREAD = threading.Thread(
            target=live_ws_worker,
            name="live-api-websocket",
            daemon=True,
        )
        LIVE_API_WS_THREAD.start()


def startup_live_endpoint() -> None:
    parse_live_api_config()
    store_live_payload(fetch_live_snapshot())
    ensure_live_ws_worker()


def get_live_payload(competition_uuid: str | None = None) -> dict:
    parse_live_api_config()
    ensure_live_ws_worker()

    with LIVE_API_STATE_LOCK:
        payload = LIVE_API_STATE_PAYLOAD

    if payload is None:
        payload = fetch_live_snapshot()
        store_live_payload(payload)

    return filter_live_payload(payload, competition_uuid)
