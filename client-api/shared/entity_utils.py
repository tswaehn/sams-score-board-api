from __future__ import annotations

from datetime import datetime, timedelta

from sams_api_client import extract_endpoint_from_url, extract_uuid_from_url
from shared.fetch_association import ASSOCIATION
from shared.fetch_season import SEASON


def seconds_until_daily_update(hour: int, minute: int) -> float:
    now = datetime.now()
    next_update = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now >= next_update:
        next_update = next_update + timedelta(days=1)
    return max((next_update - now).total_seconds(), 0.0)


def get_association_and_season(
    association_uuid: str | None,
    season_uuid: str | None,
) -> tuple[dict, dict]:
    association = ASSOCIATION.get(association_uuid) if isinstance(association_uuid, str) else {}
    season = SEASON.get(season_uuid) if isinstance(season_uuid, str) else {}
    return association, season


def build_entity_list_entry(
    *,
    entity_type: str,
    entity_uuid: str,
    name: str,
    gender: str,
    shortname: str | None,
    association: dict,
    season: dict,
    association_url: str | None = None,
    season_url: str | None = None,
) -> dict:
    entry = {
        "uuid": entity_uuid,
        "entityType": entity_type,
        "name": name,
        "gender": gender,
        "shortname": shortname,
        "currentSeason": bool(season.get("currentSeason")),
        "association": {
            "uuid": association.get("uuid"),
            "name": association.get("name"),
            "shortname": association.get("shortname"),
        },
        "season": {
            "uuid": season.get("uuid"),
            "name": season.get("name"),
        },
    }

    if association_url is not None:
        entry["association_url"] = association_url
    if season_url is not None:
        entry["season_url"] = season_url

    return entry


def build_entry_from_linked_payload(
    *,
    entity_type: str,
    payload: dict,
    association_link: str,
    season_link: str,
) -> dict:
    association_uuid = extract_uuid_from_url(association_link)
    season_uuid = extract_uuid_from_url(season_link)
    association, season = get_association_and_season(association_uuid, season_uuid)
    return build_entity_list_entry(
        entity_type=entity_type,
        entity_uuid=payload["uuid"],
        name=payload["name"],
        gender=payload["gender"],
        shortname=payload.get("shortName"),
        association=association,
        season=season,
        association_url=extract_endpoint_from_url(association_link),
        season_url=f"seasons/{season['uuid']}",
    )


def normalize_team(team: dict) -> dict:
    return {
        "uuid": team["uuid"],
        "name": team["name"],
        "shortName": team["shortName"],
        "logoImageLink": team["logoImageLink"],
    }


def normalize_match(match: dict, *, split_date: bool = False) -> dict:
    team1_link = match.get("_links", {}).get("team1")
    team2_link = match.get("_links", {}).get("team2")
    date = match.get("date")
    results = match.get("results")
    finished = isinstance(results, dict) and bool(results.get("winner"))

    return {
        "uuid": match["uuid"],
        "date": date.split("T", 1)[0] if split_date and isinstance(date, str) else date,
        "time": match.get("time"),
        "location": match.get("location"),
        "matchNumber": match.get("matchNumber"),
        "team1_uuid": extract_uuid_from_url(team1_link["href"]) if team1_link else None,
        "team2_uuid": extract_uuid_from_url(team2_link["href"]) if team2_link else None,
        "team1_name": match.get("team1Description"),
        "team2_name": match.get("team2Description"),
        "finished": finished,
        "verified": bool(match.get("verified")),
        "results": results,
    }


def normalize_ranking_entry(entry: dict, *, include_points: bool = False) -> dict:
    normalized_entry = {
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
    if include_points:
        normalized_entry["points"] = entry.get("points")
    return normalized_entry
