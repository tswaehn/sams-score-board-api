import os
import time
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
PAGE_SIZE = 100
PAGE_DELAY_SECONDS = 0.3
LAST_REQUEST_COMPLETED_AT = 0.0
ENDPOINT_CACHE: dict[str, dict] = {}


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


def fetch_endpoint(endpoint: str) -> dict:
    normalized_endpoint = endpoint.strip("/")

    if normalized_endpoint not in ENDPOINT_CACHE:
        ENDPOINT_CACHE[normalized_endpoint] = _fetch_endpoint(normalized_endpoint)

    return ENDPOINT_CACHE[normalized_endpoint]
