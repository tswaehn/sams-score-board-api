from __future__ import annotations

from competition.fetch_competition_match_group import MATCH_GROUP
from competition.fetch_competition_ranking import COMPETITION_RANKING
from competition.fetch_competition_team import COMPETITION_TEAMS
from periodic_updater import PeriodicUpdater
from sams_api_client import extract_uuid_from_url, fetch_endpoint_direct
from shared.fetch_association import ASSOCIATION
from shared.fetch_season import SEASON


STORE_TTL_SECONDS = 60


class Competition(PeriodicUpdater):
    def __init__(self) -> None:
        super().__init__(
            logger_name="api.competition",
            thread_name="competition-updater",
            store_file_name="competition-store.json",
        )

    def update_store(self, uuid: str | None = None) -> None:
        if uuid is None:
            return

        competition = fetch_endpoint_direct(f"/competitions/{uuid}")
        if not isinstance(competition, dict):
            raise RuntimeError(f"Expected competition payload to be a dict for {uuid!r}")

        self.dump_raw_json("competition-store-raw.json", uuid, competition)
        self.set_store_item(uuid, self.normalize_competition(competition), STORE_TTL_SECONDS)

    def get(self, competition_uuid: str) -> tuple[dict, bool]:
        self.wait_for_uuid(competition_uuid)

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
            "entityType": "competition",
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
            "match-groups": MATCH_GROUP.get(competition_id, current_season),
            "teams": COMPETITION_TEAMS.get(competition_id),
            "rankings": COMPETITION_RANKING.get(competition_id, current_season),
        }


COMPETITION = Competition()
