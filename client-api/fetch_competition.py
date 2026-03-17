import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlparse

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


def build_url(endpoint: str) -> str:
    normalized_endpoint = endpoint.strip("/")
    if not normalized_endpoint:
        raise RuntimeError("Endpoint must not be empty")
    return f"{API_BASE_URL}/{normalized_endpoint}"


def build_output_path(endpoint: str) -> Path:
    filename = endpoint.strip("/").replace("/", "_")
    return Path(__file__).with_name(f"{filename}.json")


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


def fetch_endpoint(endpoint: str) -> dict:
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

def get_competition_list():
    competitions = fetch_endpoint(f"/competitions")
    C = []
    for competition in competitions["content"]:
        C.append({
            "uuid": competition["uuid"],
            "name": competition["name"],
            "gender": competition["gender"],
            "shortname": competition["shortName"],
            "association_url": extract_endpoint_from_url(competition["_links"]["association"]["href"]),
            "season_url": extract_endpoint_from_url(competition["_links"]["season"]["href"]),
        })

    # cache for association and season
    A = {}
    S = {}

    for competition in C:
        if competition["association_url"] not in A:
            association = fetch_endpoint(competition["association_url"])
            A[competition["association_url"]] = association
        if competition["season_url"] not in S:
            S[competition["season_url"]] = fetch_endpoint(competition["season_url"])

        # fill from cache
        competition["association"] = {
            "uuid": A[competition["association_url"]]["uuid"],
            "name": A[competition["association_url"]]["name"],
            "shortname": A[competition["association_url"]]["shortname"],
        }

        competition["season"] = {
            "uuid": S[competition["season_url"]]["uuid"],
            "name": S[competition["season_url"]]["name"],
       }

    return C


def get_competition(competition_id: str) -> dict:
    competition = fetch_endpoint(f"/competitions/{competition_id}")
    association = fetch_endpoint(extract_endpoint_from_url(competition["_links"]["association"]["href"]))
    season = fetch_endpoint(extract_endpoint_from_url(competition["_links"]["season"]["href"]))
    match_groups = fetch_endpoint(f"/competitions/{competition_id}/match-groups")["content"]
    teams = fetch_endpoint(f"/competitions/{competition_id}/teams")["content"]
    rankings = fetch_endpoint(f"/competitions/{competition_id}/rankings")["content"]

    R = {
        "competition": {
            "uuid": competition["uuid"],
            "name": competition["name"],
            "gender": competition["gender"],
        },
        "association": {
            "uuid": association["uuid"],
            "name": association["name"],
            "shortname": association["shortname"]
        },
        "season": {
            "uuid": season["uuid"],
            "name": season["name"],
            "currentSeason": season["currentSeason"],
        },
        "match-groups": {},
        "teams": [],
        "rankings": {},
    }

    for match_group in match_groups:
        R["match-groups"][match_group["name"]] ={
            "uuid": match_group["uuid"],
            "name": match_group["name"],
            "tourneyLevel": match_group["tourneyLevel"],
            "teams": []
        }

    for team in teams:
        R["teams"].append({
            "uuid": team["uuid"],
            "name": team["name"],
            "logoImageLink": team["logoImageLink"],
        })

    for ranking in rankings:
        matchGroupName = ranking["matchGroupName"]
        R["rankings"][matchGroupName] = {}

        for entry in ranking["rankings"]:
            R["rankings"][matchGroupName][entry["rank"]] = {
                "teamName": entry["teamName"],
                "matchesPlayed": entry["matchesPlayed"],
                "wins": entry["wins"],
                "losses": entry["losses"],
                "setWins": entry["setWins"],
                "setLosses": entry["setLosses"],
                "ballWins": entry["ballWins"],
                "ballLosses": entry["ballLosses"],
                "ballDifference": entry["ballDifference"],
            }

    return R

def store_competition_list():
    competition_list = get_competition_list()
    output_path = build_output_path("competition-list")
    with open(output_path, "w", encoding="utf-8") as output_file:
        json.dump(competition_list, output_file, indent=2)
    print(json.dumps(competition_list, indent=2))


def _main() -> None:
    ## store_competition_list()

    competition_id = "71556c84-7e05-4516-88f7-4bf890f9873a"
    competition_id = "dfcdd4c1-6d94-42ce-9028-9bba43d36d56"
    competition_id = "d2f619a3-7fea-4b1e-9d86-a300e335e2ec"

    payload = get_competition(competition_id)

    output_path = build_output_path("competition")
    with open(output_path, "w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, indent=2)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    _main()
