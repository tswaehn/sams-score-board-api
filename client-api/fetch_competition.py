from fetch_association import ASSOCIATION
from fetch_match_group import MATCH_GROUP
from fetch_season import SEASON
from fetch_teams import TEAMS
from sams_api_client import extract_uuid_from_url, fetch_endpoint, fetch_endpoint_with_cache_status


def get_rankings(competition_uuid: str, current_season: bool) -> dict:
    rankings = fetch_endpoint(
        f"/competitions/{competition_uuid}/rankings",
        current_season=current_season,
    )["content"]
    result = {}

    for ranking in rankings:
        match_group_name = ranking["matchGroupName"]
        result[match_group_name] = {}

        for entry in ranking["rankings"]:
            result[match_group_name][entry["rank"]] = {
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

    return result
def get_competition(competition_id: str) -> tuple[dict, bool]:
    competition, was_cached = fetch_endpoint_with_cache_status(f"/competitions/{competition_id}")

    association_uuid = extract_uuid_from_url(competition["_links"]["association"]["href"])
    season_uuid = extract_uuid_from_url(competition["_links"]["season"]["href"])
    season = SEASON.get(season_uuid)
    current_season = bool(season["currentSeason"])

    result = {
        "competition": {
            "uuid": competition["uuid"],
            "name": competition["name"],
            "gender": competition["gender"],
            "association_uuid": association_uuid,
            "season_uuid": season_uuid,
            "match_groups_uuid": competition_id,
            "teams_uuid": competition_id,
            "rankings_uuid": competition_id,
        },
        "association": ASSOCIATION.get(association_uuid, current_season=current_season),
        "season": season,
        "match-groups": MATCH_GROUP.get_by_competition_uuid(competition_id, current_season),
        "teams": TEAMS.get_by_competition_uuid(competition_id, current_season=current_season),
        "rankings": get_rankings(competition_id, current_season),
    }

    return result, was_cached
