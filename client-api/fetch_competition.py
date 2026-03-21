from sams_api_client import extract_uuid_from_url, fetch_endpoint


def get_association(association_uuid: str) -> dict:
    association = fetch_endpoint(f"/associations/{association_uuid}")
    return {
        "uuid": association["uuid"],
        "name": association["name"],
        "shortname": association["shortname"],
    }


def get_season(season_uuid: str) -> dict:
    season = fetch_endpoint(f"/seasons/{season_uuid}")
    return {
        "uuid": season["uuid"],
        "name": season["name"],
        "currentSeason": season["currentSeason"],
    }


def get_match_groups(competition_uuid: str) -> dict:
    match_groups = fetch_endpoint(f"/competitions/{competition_uuid}/match-groups")["content"]
    result = {}

    for match_group in match_groups:
        matches_uuid = extract_uuid_from_url(match_group["_links"]["matches"]["href"])
        result[match_group["name"]] = {
            "uuid": match_group["uuid"],
            "name": match_group["name"],
            "tourneyLevel": match_group["tourneyLevel"],
            "matches_uuid": matches_uuid,
        }
        t = get_competition_matches(matches_uuid)
        result[match_group["name"]]["matches"] = t

    return result


def get_teams(competition_uuid: str) -> list[dict]:
    teams = fetch_endpoint(f"/competitions/{competition_uuid}/teams")["content"]
    result = []

    for team in teams:
        result.append({
            "uuid": team["uuid"],
            "name": team["name"],
            "shortName": team["shortName"],
            "logoImageLink": team["logoImageLink"],
        })

    return result


def get_rankings(competition_uuid: str) -> dict:
    rankings = fetch_endpoint(f"/competitions/{competition_uuid}/rankings")["content"]
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

def get_competition_matches(competition_uuid: str) -> dict:
    matches = fetch_endpoint(f"/match-groups/{competition_uuid}/competition-matches")["content"]
    result = {}
    for match in matches:
        team1_link = match["_links"].get("team1")
        team2_link = match["_links"].get("team2")
        team1_uuid = extract_uuid_from_url(team1_link["href"]) if team1_link else None
        team2_uuid = extract_uuid_from_url(team2_link["href"]) if team2_link else None
        result[match["uuid"]] = {
            "uuid": match["uuid"],
            "date": match["date"],
            "time": match["time"],
            "location": match["location"],
            "matchNumber": match["matchNumber"],
            "team1_uuid": team1_uuid,
            "team2_uuid": team2_uuid,
            "team1_name": match["team1Description"],
            "team2_name": match["team2Description"],
            "results": match["results"],
        }
    return result

def get_competition(competition_id: str) -> dict:
    competition = fetch_endpoint(f"/competitions/{competition_id}")

    association_uuid = extract_uuid_from_url(competition["_links"]["association"]["href"])
    season_uuid = extract_uuid_from_url(competition["_links"]["season"]["href"])

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
        "association": get_association(association_uuid),
        "season": get_season(season_uuid),
        "match-groups": get_match_groups(competition_id),
        "teams": get_teams(competition_id),
        "rankings": get_rankings(competition_id),
    }

    return result
