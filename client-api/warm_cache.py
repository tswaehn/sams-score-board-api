from __future__ import annotations

from sams_api_client import fetch_endpoint


def fetch_seasons() -> list[dict]:
    seasons_payload = fetch_endpoint("/seasons")
    if not isinstance(seasons_payload, list):
        raise RuntimeError("Expected /seasons to return a list payload")
    return [season for season in seasons_payload if isinstance(season, dict)]


def build_season_ranges(seasons: list[dict]) -> list[dict]:
    ranges: list[dict] = []

    for season in seasons:
        ranges.append(
            {
                "uuid": season.get("uuid"),
                "name": season.get("name"),
                "startDate": season.get("startDate"),
                "endDate": season.get("endDate"),
                "currentSeason": season.get("currentSeason"),
            }
        )

    ranges.sort(key=lambda item: (str(item["startDate"]), str(item["name"])))
    return ranges


def warm_cache() -> None:
    seasons = fetch_seasons()
    season_ranges = build_season_ranges(seasons)

    print(f"Fetched {len(season_ranges)} seasons")
    print("Season ranges:")
    for season in season_ranges:
        print(
            f"- {season['name']} "
            f"uuid={season['uuid']} "
            f"startDate={season['startDate']} "
            f"endDate={season['endDate']} "
            f"currentSeason={season['currentSeason']}"
        )


if __name__ == "__main__":
    warm_cache()
