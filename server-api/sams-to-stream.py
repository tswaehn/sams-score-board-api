from confluent_kafka import Consumer, KafkaError
from typing import Optional
import json
from urllib.error import HTTPError, URLError
import urllib.request
from config import CONFIG


def execute_get_request(url = None):
    """Execute a HTTP GET request using ``url`` or the configured default."""
    target_url = url or CONFIG.default_url
    if not target_url:
        raise ValueError("No URL provided and no default configured.")

    try:
        with urllib.request.urlopen(target_url) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            json_resp = json.loads(response.read().decode(charset))
            with open("response.json", "w") as f:
                json.dump(json_resp, f, indent=2)
            return json_resp
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"GET request to {target_url!r} failed: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to decode JSON from {target_url!r}: {exc}") from exc

def decode_match_series(document: dict) -> dict:
    raw_match_series = document.get("matchSeries", {})

    all_series = {}
    for series_uuid, series_info in raw_match_series.items():
        class_type = series_info.get("class", "")
        if class_type not in all_series:
            all_series[class_type] = {}

        all_series[class_type][series_info["orderLevel"]] = {
            "name": series_info["name"],
            "id": series_uuid,
            "gender": series_info["gender"],
        }
    return all_series

def print_all_series(series: dict):
    for class_type, series_list in series.items():
        print(f"Class: {class_type}")
        for order_level, series_info in series_list.items():
            print(f"Order Level: {order_level}, Series Name: {series_info['name']}, Series ID: {series_info['id']}, Gender: {series_info['gender']}")


def decode_competition(document: dict, competition_id: str) -> dict:
    match_series = document.get("matchSeries", {})
    competition = match_series.get(competition_id, {})
    return competition



def _main():

    competition_id = CONFIG.competition_id
    try:
        response = execute_get_request()
        all_series = decode_match_series(response)
        print_all_series(all_series)

        competition = decode_competition(response, competition_id)
        print(competition)
    except Exception as exc:
        print(f"An error occurred: {exc}")
        raise

if __name__ == "__main__":
    _main()
