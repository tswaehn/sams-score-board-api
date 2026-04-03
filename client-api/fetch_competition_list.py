from __future__ import annotations

import threading

from sams_api_client import extract_endpoint_from_url, fetch_endpoint


COMPETITION_LIST_LOCK = threading.RLock()
COMPETITION_LIST_BY_UUID: dict[str, dict] = {}
COMPETITION_UUIDS_BY_SEASON: dict[str, set[str]] = {}


def verify_competition_list(competition_list: list[dict]) -> list[dict]:
    verified_competitions = []
    seen_uuids = set()

    for competition in competition_list:
        competition_uuid = competition["uuid"]
        if competition_uuid in seen_uuids:
            continue

        seen_uuids.add(competition_uuid)
        verified_competitions.append(competition)

    return verified_competitions


def _get_cached_association(association_url: str, association_cache: dict[str, dict]) -> dict:
    association = association_cache.get(association_url)
    if association is None:
        payload = fetch_endpoint(association_url)
        if not isinstance(payload, dict):
            raise RuntimeError(f"Expected association payload to be a dict for {association_url!r}")
        association_cache[association_url] = payload
        association = payload
    return association


def _get_season_payload(season_uuid: str) -> dict:
    payload = fetch_endpoint(f"/seasons/{season_uuid}")
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected season payload to be a dict for {season_uuid!r}")
    return payload


def _build_competition_entry(competition: dict, association_cache: dict[str, dict], season_payload: dict) -> dict:
    association_url = extract_endpoint_from_url(competition["_links"]["association"]["href"])
    association = _get_cached_association(association_url, association_cache)

    return {
        "uuid": competition["uuid"],
        "name": competition["name"],
        "gender": competition["gender"],
        "shortname": competition["shortName"],
        "currentSeason": bool(season_payload.get("currentSeason", True)),
        "association_url": association_url,
        "season_url": f"seasons/{season_payload['uuid']}",
        "association": {
            "uuid": association["uuid"],
            "name": association["name"],
            "shortname": association["shortname"],
        },
        "season": {
            "uuid": season_payload["uuid"],
            "name": season_payload["name"],
        },
    }


def _store_competitions_for_season(season_uuid: str, competition_list: list[dict]) -> list[dict]:
    updated_competitions = verify_competition_list(competition_list)
    updated_competition_ids = {competition["uuid"] for competition in updated_competitions}

    with COMPETITION_LIST_LOCK:
        previous_competition_ids = COMPETITION_UUIDS_BY_SEASON.get(season_uuid, set())
        for competition_uuid in previous_competition_ids - updated_competition_ids:
            COMPETITION_LIST_BY_UUID.pop(competition_uuid, None)

        for competition in updated_competitions:
            COMPETITION_LIST_BY_UUID[competition["uuid"]] = competition

        COMPETITION_UUIDS_BY_SEASON[season_uuid] = updated_competition_ids
        return verify_competition_list(list(COMPETITION_LIST_BY_UUID.values()))


def update_competition_list_by_season(season_uuid: str) -> list[dict]:
    season_payload = _get_season_payload(season_uuid)
    competitions_payload = fetch_endpoint(f"/competitions?season={season_uuid}")
    if not isinstance(competitions_payload, dict):
        raise RuntimeError(f"Expected competition list payload to be a dict for season {season_uuid!r}")

    competitions = competitions_payload.get("content", [])
    if not isinstance(competitions, list):
        raise RuntimeError(f"Expected competition list content to be a list for season {season_uuid!r}")

    association_cache: dict[str, dict] = {}
    season_competitions = [
        _build_competition_entry(competition, association_cache, season_payload)
        for competition in competitions
    ]
    return _store_competitions_for_season(season_uuid, season_competitions)


def update_competition_list() -> list[dict]:
    seasons_payload = fetch_endpoint("/seasons")
    if not isinstance(seasons_payload, list):
        raise RuntimeError("Expected /seasons to return a list payload")

    updated_competition_list: list[dict] = []
    for season in seasons_payload:
        season_uuid = season.get("uuid")
        if not isinstance(season_uuid, str):
            continue
        updated_competition_list = update_competition_list_by_season(season_uuid)

    return updated_competition_list
