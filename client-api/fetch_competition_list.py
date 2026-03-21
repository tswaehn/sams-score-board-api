from sams_api_client import extract_endpoint_from_url, fetch_endpoint


def get_competition_list():
    competitions = fetch_endpoint("/competitions")
    competition_list = []
    association_cache = {}
    season_cache = {}

    for competition in competitions["content"]:
        competition_list.append({
            "uuid": competition["uuid"],
            "name": competition["name"],
            "gender": competition["gender"],
            "shortname": competition["shortName"],
            "association_url": extract_endpoint_from_url(competition["_links"]["association"]["href"]),
            "season_url": extract_endpoint_from_url(competition["_links"]["season"]["href"]),
        })

    for competition in competition_list:
        association_url = competition["association_url"]
        season_url = competition["season_url"]

        if association_url not in association_cache:
            association_cache[association_url] = fetch_endpoint(association_url)
        if season_url not in season_cache:
            season_cache[season_url] = fetch_endpoint(season_url)

        competition["association"] = {
            "uuid": association_cache[association_url]["uuid"],
            "name": association_cache[association_url]["name"],
            "shortname": association_cache[association_url]["shortname"],
        }
        competition["season"] = {
            "uuid": season_cache[season_url]["uuid"],
            "name": season_cache[season_url]["name"],
        }

    return competition_list
