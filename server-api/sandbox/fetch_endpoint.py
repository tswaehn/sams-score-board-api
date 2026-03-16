import json
import os
from pathlib import Path
import sys
import time

import requests
from requests import RequestException


API_BASE_URL = "https://www.ssvb.org/api/v2"
DEFAULT_ENDPOINT = "competitions"

# DEFAULT_ENDPOINT = "match-groups"
# DEFAULT_ENDPOINT = "competition-matches"

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


def build_url(endpoint: str) -> str:
    normalized_endpoint = endpoint.strip("/")
    if not normalized_endpoint:
        raise RuntimeError("Endpoint must not be empty")
    return f"{API_BASE_URL}/{normalized_endpoint}"


def build_output_path(endpoint: str) -> Path:
    filename = endpoint.strip("/").replace("/", "_")
    return Path(__file__).with_name(f"{filename}.json")


def fetch_page(url: str, api_key: str, page: int, size: int = PAGE_SIZE) -> dict:
    response = None
    try:
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
        return response.json()
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


def fetch_resource(endpoint: str = DEFAULT_ENDPOINT) -> list | dict:
    api_key = os.getenv("SSVB_API_KEY")
    if not api_key:
        raise RuntimeError("Missing environment variable: SSVB_API_KEY")

    url = build_url(endpoint)
    first_page = fetch_page(url, api_key, page=0)

    if not isinstance(first_page, dict) or "content" not in first_page:
        return first_page

    all_items = list(first_page.get("content", []))
    total_elements = first_page.get("totalElements", len(all_items))
    page = 1

    while len(all_items) < total_elements:
        time.sleep(0.3)
        page_data = fetch_page(url, api_key, page=page)
        page_items = page_data.get("content", [])
        if not page_items:
            break
        all_items.extend(page_items)
        page += 1

    combined_response = dict(first_page)
    combined_response["content"] = all_items
    combined_response["numberOfElements"] = len(all_items)
    combined_response["size"] = PAGE_SIZE
    combined_response["pagesFetched"] = page
    return combined_response


def _main() -> None:
    endpoint = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ENDPOINT
    resource = fetch_resource(endpoint)
    output_path = build_output_path(endpoint)
    with open(output_path, "w", encoding="utf-8") as output_file:
        json.dump(resource, output_file, indent=2)
    print(json.dumps(resource, indent=2))


if __name__ == "__main__":
    _main()
