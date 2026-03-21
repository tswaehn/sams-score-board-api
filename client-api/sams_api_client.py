import hashlib
import json
import os
import threading
import time
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

import requests
from requests import RequestException


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
DEFAULT_CACHE_DURATION_SECONDS = 24 * 60 * 60
LAST_REQUEST_COMPLETED_AT = 0.0
CACHE_DIR = Path(__file__).with_name("cache")
ENDPOINT_CACHE_FILE_PREFIX = "endpoint_cache_"
ENDPOINT_CACHE: dict[str, dict] = {}
CACHE_LOCK = threading.RLock()
ENDPOINT_FETCH_LOCKS: dict[str, threading.Lock] = {}
WARM_CACHE_THREAD: threading.Thread | None = None


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

    now = time.monotonic()
    elapsed = now - LAST_REQUEST_COMPLETED_AT
    if elapsed < min_delay_seconds:
        time.sleep(min_delay_seconds - elapsed)


def fetch_page(url: str, api_key: str, page: int, size: int = PAGE_SIZE) -> dict:
    response = None
    try:
        wait_for_request_slot()
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
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError(f"Expected a dict payload for page {page}, got {type(payload).__name__}")
        return payload
    except RequestException as exc:
        raise RuntimeError(f"Request to {url!r} failed on page {page}: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError(
            f"Failed to decode JSON from {url!r} on page {page}: {exc}"
        ) from exc
    finally:
        if response is not None:
            print(f"HTTP status: {response.status_code} (page {page})")
        else:
            print(f"HTTP status: no response received (page {page})")
        globals()["LAST_REQUEST_COMPLETED_AT"] = time.monotonic()


def _fetch_endpoint(endpoint: str) -> dict:
    api_key = os.getenv("SSVB_API_KEY")
    if not api_key:
        raise RuntimeError("Missing environment variable: SSVB_API_KEY")

    url = build_url(endpoint)
    first_page = fetch_page(url, api_key, page=0)

    if "content" not in first_page:
        return first_page

    all_items = list(first_page.get("content", []))
    total_elements = first_page.get("totalElements", len(all_items))
    pages_fetched = 1
    page = 1

    while len(all_items) < total_elements:
        page_data = fetch_page(url, api_key, page=page)
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


def _build_cache_file_path(endpoint: str) -> Path:
    endpoint_hash = hashlib.sha256(endpoint.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{ENDPOINT_CACHE_FILE_PREFIX}{endpoint_hash}.json"


def _get_endpoint_fetch_lock(endpoint: str) -> threading.Lock:
    with CACHE_LOCK:
        endpoint_lock = ENDPOINT_FETCH_LOCKS.get(endpoint)
        if endpoint_lock is None:
            endpoint_lock = threading.Lock()
            ENDPOINT_FETCH_LOCKS[endpoint] = endpoint_lock
        return endpoint_lock


def load_cache() -> None:
    global WARM_CACHE_THREAD

    CACHE_DIR.mkdir(exist_ok=True)

    for cache_file in CACHE_DIR.glob(f"{ENDPOINT_CACHE_FILE_PREFIX}*.json"):
        try:
            with cache_file.open("r", encoding="utf-8") as input_file:
                cache_entry = json.load(input_file)
        except (OSError, json.JSONDecodeError):
            continue

        endpoint = cache_entry.get("endpoint")
        cache_timestamp = cache_entry.get("cache_timestamp")
        value = cache_entry.get("value")

        if not isinstance(endpoint, str):
            continue
        if not isinstance(cache_timestamp, (int, float)):
            continue
        if not isinstance(value, dict):
            continue

        with CACHE_LOCK:
            ENDPOINT_CACHE[endpoint] = {
                "cache_timestamp": cache_timestamp,
                "cache_file": str(cache_file),
                "value": value,
            }

    if WARM_CACHE_THREAD is None or not WARM_CACHE_THREAD.is_alive():
        def warm_cache_runner() -> None:
            from warm_cache import warm_cache

            warm_cache()

        WARM_CACHE_THREAD = threading.Thread(target=warm_cache_runner, name="warm-cache", daemon=True)
        WARM_CACHE_THREAD.start()

    return


def _get_cached_value(endpoint: str, cache_duration_seconds: float) -> dict | None:
    with CACHE_LOCK:
        cache_entry = ENDPOINT_CACHE.get(endpoint)
        if cache_entry is None:
            return None

        cache_timestamp = cache_entry["cache_timestamp"]
        if time.time() - cache_timestamp > cache_duration_seconds:
            return None

        return cache_entry["value"]


def _cache_value(endpoint: str, value: dict) -> dict:
    CACHE_DIR.mkdir(exist_ok=True)
    cache_timestamp = time.time()
    cache_file = _build_cache_file_path(endpoint)
    serialized_entry = {
        "endpoint": endpoint,
        "cache_timestamp": cache_timestamp,
        "value": value,
    }

    with cache_file.open("w", encoding="utf-8") as output_file:
        json.dump(serialized_entry, output_file)

    with CACHE_LOCK:
        ENDPOINT_CACHE[endpoint] = {
            "cache_timestamp": cache_timestamp,
            "cache_file": str(cache_file),
            "value": value,
        }
        return ENDPOINT_CACHE[endpoint]["value"]


def fetch_endpoint_with_cache_status(
    endpoint: str,
    cache_duration_seconds: float = DEFAULT_CACHE_DURATION_SECONDS,
) -> tuple[dict, bool]:
    normalized_endpoint = endpoint.strip("/")
    cached_value = _get_cached_value(normalized_endpoint, cache_duration_seconds)

    if cached_value is not None:
        return cached_value, True

    endpoint_lock = _get_endpoint_fetch_lock(normalized_endpoint)
    with endpoint_lock:
        cached_value = _get_cached_value(normalized_endpoint, cache_duration_seconds)
        if cached_value is not None:
            return cached_value, True

        return _cache_value(normalized_endpoint, _fetch_endpoint(normalized_endpoint)), False


def fetch_endpoint(endpoint: str, cache_duration_seconds: float = DEFAULT_CACHE_DURATION_SECONDS) -> dict:
    value, _ = fetch_endpoint_with_cache_status(endpoint, cache_duration_seconds=cache_duration_seconds)
    return value


load_cache()
