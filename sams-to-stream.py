from confluent_kafka import Consumer, KafkaError
from typing import Optional
import json
from urllib.error import HTTPError, URLError
import urllib.request
from config import CONFIG


def execute_get_request(url: Optional[str] = None) -> str:
    """Execute a HTTP GET request using ``url`` or the configured default."""
    target_url = url or CONFIG.default_url
    if not target_url:
        raise ValueError("No URL provided and no default configured.")

    try:
        with urllib.request.urlopen(target_url) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return json.loads(response.read().decode(charset))
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"GET request to {target_url!r} failed: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to decode JSON from {target_url!r}: {exc}") from exc

def decode_match_series(document: dict) -> dict:
    raw_match_series = document.get("matchSeries", {})

    series = {}
    for series_uuid, series_info in raw_match_series.items():
        class_type = series_info.get("class", "")
        if class_type not in series:
            series[class_type] = {}

        series[class_type][series_info["orderLevel"]] = {
            "name": series_info["name"],
            "id": series_uuid,
            "gender": series_info["gender"],
        }
    return series

def _main():
    try:
        response = execute_get_request()

        series = decode_match_series(response)
        print(series)
    except Exception as exc:
        print(f"An error occurred: {exc}")
        raise

if __name__ == "__main__":
    _main()
