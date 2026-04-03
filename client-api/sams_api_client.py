from __future__ import annotations

import logging
import os
import threading
import time
from urllib.parse import urlparse
from uuid import UUID

import requests
from requests import RequestException

from endpoint_cache import (
    CachedObject,
    CompetitionCachedObject,
    cached_object_from_endpoint,
    get_cached_json,
)


LOGGER = logging.getLogger("competition-api.client")

API_BASE_URL = "https://www.ssvb.org/api/v2"
DEFAULT_HEADERS = {
    "Accept": "*/*",
    "Connection": "close",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.0 Safari/537.36"
    ),
}
PAGE_SIZE = 9999
PAGE_DELAY_SECONDS = 0.3
LAST_REQUEST_COMPLETED_AT = 0.0
LAST_REQUEST_LOCK = threading.Lock()


def build_url(endpoint: str) -> str:
    normalized_endpoint = endpoint.strip("/")
    if not normalized_endpoint:
        raise RuntimeError("Endpoint must not be empty")
    return f"{API_BASE_URL}/{normalized_endpoint}"


def extract_endpoint_from_url(url: str) -> str:
    parsed_url = urlparse(url.strip())
    path = parsed_url.path.strip("/")
    api_prefix = "api/v2/"

    if not path.startswith(api_prefix):
        raise RuntimeError(f"URL does not contain the expected API prefix: {url!r}")

    endpoint = path.removeprefix(api_prefix)
    if not endpoint:
        raise RuntimeError(f"URL does not contain an endpoint after the API prefix: {url!r}")

    return endpoint


def extract_uuid_from_url(url: str) -> str:
    endpoint = extract_endpoint_from_url(url)

    for segment in endpoint.split("/"):
        try:
            return str(UUID(segment))
        except ValueError:
            continue

    raise RuntimeError(f"URL does not contain a UUID segment: {url!r}")


def wait_for_request_slot(min_delay_seconds: float = PAGE_DELAY_SECONDS) -> None:
    global LAST_REQUEST_COMPLETED_AT

    while True:
        with LAST_REQUEST_LOCK:
            now = time.monotonic()
            elapsed = now - LAST_REQUEST_COMPLETED_AT
            if elapsed >= min_delay_seconds:
                LAST_REQUEST_COMPLETED_AT = now
                return
            remaining_delay = min_delay_seconds - elapsed

        time.sleep(remaining_delay)


def fetch_page(
    url: str,
    api_key: str,
    page: int,
    size: int = PAGE_SIZE,
    *,
    total_pages: int | None = None,
) -> dict | list:
    try:
        wait_for_request_slot()
        started_at = time.monotonic()
        headers = {
            **DEFAULT_HEADERS,
            "X-Api-Key": api_key,
            "page": str(page),
            "size": str(size),
        }
        response = requests.get(
            url,
            headers=headers,
            params={"page": page, "size": size},
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
        duration_ms = (time.monotonic() - started_at) * 1000.0
        if not isinstance(payload, (dict, list)):
            raise RuntimeError(f"Expected a JSON payload for page {page}, got {type(payload).__name__}")

        progress_percent = None
        if isinstance(payload, dict):
            content = payload.get("content")
            if isinstance(content, list):
                if total_pages is None:
                    payload_total_pages = payload.get("totalPages")
                    if isinstance(payload_total_pages, int):
                        total_pages = max(payload_total_pages, 1)

        if total_pages is not None:
            if total_pages <= 0:
                progress_percent = 100.0
            else:
                progress_percent = min(page + 1, total_pages) / total_pages * 100.0

        progress_label = f"{progress_percent:.1f}%" if progress_percent is not None else "n/a"
        LOGGER.info(
            "Fetched upstream page url=%s page=%s status=%s totalPages=%s progress=%s durationMs=%.1f",
            url,
            page,
            response.status_code,
            total_pages,
            progress_label,
            duration_ms,
        )
        return payload
    except RequestException as exc:
        raise RuntimeError(f"Request to {url!r} failed on page {page}: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError(f"Failed to decode JSON from {url!r} on page {page}: {exc}") from exc


def _fetch_endpoint_from_upstream(endpoint: str) -> dict | list:
    api_key = os.getenv("SSVB_API_KEY")
    if not api_key:
        raise RuntimeError("Missing environment variable: SSVB_API_KEY")

    url = build_url(endpoint)
    first_page = fetch_page(url, api_key, page=0)
    if isinstance(first_page, list):
        return first_page

    if "content" not in first_page:
        return first_page

    all_items = list(first_page.get("content", []))
    total_elements = first_page.get("totalElements", len(all_items))
    total_pages = first_page.get("totalPages")
    if not isinstance(total_pages, int):
        total_pages = None
    pages_fetched = 1
    page = 1

    while len(all_items) < total_elements:
        page_data = fetch_page(
            url,
            api_key,
            page=page,
            total_pages=total_pages,
        )
        page_items = page_data.get("content", [])
        if not page_items:
            break
        all_items.extend(page_items)
        page += 1
        pages_fetched += 1

    aggregated_response = dict(first_page)
    aggregated_response["content"] = all_items
    aggregated_response["numberOfElements"] = len(all_items)
    aggregated_response["size"] = PAGE_SIZE
    aggregated_response["pagesFetched"] = pages_fetched
    return aggregated_response


def _resolve_competition_cached_object(
    competition_payload: dict,
    requested_object: CompetitionCachedObject,
) -> CompetitionCachedObject:
    season_link = competition_payload.get("_links", {}).get("season", {}).get("href")
    if not isinstance(season_link, str):
        return requested_object

    season_endpoint = extract_endpoint_from_url(season_link)
    season_payload = fetch_endpoint(season_endpoint)
    if not isinstance(season_payload, dict):
        raise RuntimeError(f"Expected season payload to be a dict for {season_endpoint!r}")

    return CompetitionCachedObject(
        current_season=bool(season_payload.get("currentSeason")),
        competition_uuid=requested_object.competition_uuid,
    )


def fetch_endpoint_direct(endpoint: str) -> dict | list:
    normalized_endpoint = endpoint.strip("/")
    if not normalized_endpoint:
        raise RuntimeError("Endpoint must not be empty")
    try:
        return _fetch_endpoint_from_upstream(normalized_endpoint)
    except Exception:
        LOGGER.exception(
            "Direct upstream fetch failed for endpoint=%s",
            normalized_endpoint,
        )
        return {}


def fetch_endpoint_with_cache_status(
    endpoint: str,
    *,
    current_season: bool | None = None,
) -> tuple[dict | list, bool]:
    normalized_endpoint = endpoint.strip("/")
    cached_object = cached_object_from_endpoint(
        normalized_endpoint,
        current_season=current_season,
    )

    def fetcher() -> dict | list | tuple[dict | list, CachedObject]:
        payload = _fetch_endpoint_from_upstream(normalized_endpoint)
        if isinstance(cached_object, CompetitionCachedObject):
            if not isinstance(payload, dict):
                raise RuntimeError(
                    f"Expected competition payload to be a dict for {normalized_endpoint!r}"
                )
            return payload, _resolve_competition_cached_object(payload, cached_object)
        return payload

    return get_cached_json(
        cached_object=cached_object,
        fetcher=fetcher,
    )


def fetch_endpoint(
    endpoint: str,
    *,
    current_season: bool | None = None,
) -> dict | list:
    payload, _ = fetch_endpoint_with_cache_status(
        endpoint,
        current_season=current_season,
    )
    return payload
