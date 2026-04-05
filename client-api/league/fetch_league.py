from __future__ import annotations

from league.fetch_league_match_day import LEAGUE_MATCH_DAY_STORE
from league.fetch_league_ranking import LEAGUE_RANKING
from periodic_updater import PeriodicUpdater
from sams_api_client import fetch_endpoint_direct
from shared.fetch_association import ASSOCIATION
from shared.fetch_season import SEASON
from shared.fetch_teams import TEAMS


STORE_TTL_SECONDS = 60


class League(PeriodicUpdater):
    def __init__(self) -> None:
        super().__init__(
            logger_name="competition-api.league",
            thread_name="league-updater",
            store_file_name="league-store.json",
            ttl_seconds=STORE_TTL_SECONDS,
        )

    def update_store(self, uuid: str | None = None) -> None:
        if uuid is None:
            return

        league = fetch_endpoint_direct(f"/leagues/{uuid}")
        if not isinstance(league, dict):
            raise RuntimeError(f"Expected league payload to be a dict for {uuid!r}")

        self.dump_raw_json("league-store-raw.json", uuid, league)
        self.set_store_item(uuid, self.normalize_league(league))

    def get(self, league_uuid: str) -> tuple[dict, bool]:
        self.wait_for_uuid(league_uuid)

        was_cached = self.get_store_item(league_uuid) is not None
        league = self.get_store_item(league_uuid)
        if league is None:
            raise KeyError(f"League {league_uuid!r} not found in store")
        return league, was_cached

    def normalize_league(self, league: dict) -> dict:
        association_uuid = league.get("associationUuid")
        season_uuid = league.get("seasonUuid")
        association = ASSOCIATION.get(association_uuid) if isinstance(association_uuid, str) else {}
        season = SEASON.get(season_uuid) if isinstance(season_uuid, str) else {}
        team_payload = fetch_endpoint_direct(f"/leagues/{league['uuid']}/teams")
        teams = []
        if isinstance(team_payload, dict):
            for team in team_payload.get("content", []):
                if not isinstance(team, dict):
                    continue
                team_uuid = team.get("uuid")
                if not isinstance(team_uuid, str):
                    continue
                teams.append(TEAMS.get(team_uuid))

        return {
            "entityType": "league",
            "league": {
                "uuid": league["uuid"],
                "name": league["name"],
                "shortname": league.get("shortName"),
                "gender": league["gender"],
                "association_uuid": association_uuid,
                "season_uuid": season_uuid,
                "match_days_uuid": league["uuid"],
                "teams_uuid": league["uuid"],
                "rankings_uuid": league["uuid"],
            },
            "association": association,
            "season": season,
            "match-days": LEAGUE_MATCH_DAY_STORE.get(league["uuid"]),
            "teams": teams,
            "rankings": LEAGUE_RANKING.get(league["uuid"]),
        }


LEAGUE = League()
