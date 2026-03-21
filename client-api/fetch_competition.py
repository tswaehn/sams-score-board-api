from sams_api_client import extract_endpoint_from_url, fetch_endpoint


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
