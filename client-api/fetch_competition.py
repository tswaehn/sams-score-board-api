from __future__ import annotations

from fetch_association import ASSOCIATION
from fetch_competition_ranking import COMPETITION_RANKING
from fetch_competition_team import COMPETITION_TEAMS
from fetch_match_group import MATCH_GROUP
from fetch_season import SEASON
from periodic_updater import PeriodicUpdater
from sams_api_client import extract_uuid_from_url, fetch_endpoint_direct


STORE_TTL_SECONDS = 24 * 60 * 60


class Competition(PeriodicUpdater):
    def __init__(self) -> None:
        super().__init__(
            logger_name="competition-api.competition",
            thread_name="competition-updater",
            store_file_name="competition-store.json",
            ttl_seconds=STORE_TTL_SECONDS,
        )

    def update_all(self) -> None:
        payload = fetch_endpoint_direct("/competitions")
        if not isinstance(payload, dict):
            raise RuntimeError("Expected /competitions payload to be a dict")

        competitions = payload.get("content", [])
        if not isinstance(competitions, list):
            raise RuntimeError("Expected /competitions content to be a list")

        normalized_competitions: dict[str, dict] = {}
        for competition in competitions:
            if not isinstance(competition, dict):
                continue

            competition_uuid = competition.get("uuid")
            if not isinstance(competition_uuid, str):
                continue

            normalized_competitions[competition_uuid] = self.normalize_competition(competition)

        self.dump_raw_json("competition-store-raw.json", payload)
        self.replace_store(normalized_competitions)

    def get(self, competition_uuid: str) -> tuple[dict, bool]:
        self.wait_until_store_loaded()

        was_cached = self.get_store_item(competition_uuid) is not None
        competition = self.get_store_item(competition_uuid)
        if competition is None:
            raise KeyError(f"Competition {competition_uuid!r} not found in store")
        return competition, was_cached

    def normalize_competition(self, competition: dict) -> dict:
        association_uuid = extract_uuid_from_url(competition["_links"]["association"]["href"])
        season_uuid = extract_uuid_from_url(competition["_links"]["season"]["href"])
        season = SEASON.get(season_uuid)
        current_season = bool(season["currentSeason"])
        competition_id = competition["uuid"]

        return {
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
            "association": ASSOCIATION.get(association_uuid),
            "season": season,
            "match-groups": MATCH_GROUP.get_by_competition_uuid(competition_id, current_season),
            "teams": COMPETITION_TEAMS.get(competition_id),
            "rankings": COMPETITION_RANKING.get(competition_id, current_season),
        }


COMPETITION = Competition()
