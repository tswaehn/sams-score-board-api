from __future__ import annotations

import copy

from periodic_updater import PeriodicUpdater
from sams_api_client import fetch_endpoint_direct


STORE_TTL_SECONDS = 24 * 60 * 60


class Teams(PeriodicUpdater):
    def __init__(self) -> None:
        self.teams_by_competition_uuid: dict[str, list[dict]] = {}
        super().__init__(
            logger_name="competition-api.teams",
            thread_name="teams-updater",
            store_file_name="teams-store.json",
            ttl_seconds=STORE_TTL_SECONDS,
            update_callback=self.updateAll,
        )

    def _normalize_team(self, team: dict) -> dict:
        return {
            "uuid": team["uuid"],
            "name": team["name"],
            "shortName": team["shortName"],
            "logoImageLink": team["logoImageLink"],
        }

    def _fetch_teams_for_competition(self, competition_uuid: str) -> tuple[dict, list[dict]]:
        payload = fetch_endpoint_direct(f"/competitions/{competition_uuid}/teams")
        if not isinstance(payload, dict):
            raise RuntimeError(f"Expected teams payload to be a dict for {competition_uuid!r}")

        teams = payload.get("content", [])
        if not isinstance(teams, list):
            raise RuntimeError(f"Expected teams content to be a list for {competition_uuid!r}")

        normalized_teams = []
        for team in teams:
            if not isinstance(team, dict):
                continue

            normalized_teams.append(self._normalize_team(team))

        return payload, normalized_teams

    def _fetch_all_teams(self) -> tuple[dict, list[dict]]:
        payload = fetch_endpoint_direct("/teams")
        if not isinstance(payload, dict):
            raise RuntimeError("Expected /teams payload to be a dict")

        teams = payload.get("content", [])
        if not isinstance(teams, list):
            raise RuntimeError("Expected /teams content to be a list")

        normalized_teams = []
        for team in teams:
            if not isinstance(team, dict):
                continue
            normalized_teams.append(self._normalize_team(team))

        return payload, normalized_teams

    def update(self, competition_uuid: str, current_season: bool | None = None) -> list[dict]:
        raw_payload, teams = self._fetch_teams_for_competition(competition_uuid)
        with self.lock:
            self.teams_by_competition_uuid[competition_uuid] = teams
            next_store = dict(self.store)
            for team in teams:
                next_store[team["uuid"]] = team
        self.dump_raw_json(f"teams-store-raw-competition-{competition_uuid}.json", raw_payload)
        self.replace_store(next_store)
        return copy.deepcopy(teams)

    def updateAll(self, current_season: bool | None = None) -> list[dict]:
        raw_payload, teams = self._fetch_all_teams()
        self.dump_raw_json("teams-store-raw.json", raw_payload)
        self.replace_store({team["uuid"]: team for team in teams})
        return copy.deepcopy(teams)

    def get_by_competition_uuid(
        self,
        competition_uuid: str,
        current_season: bool | None = None,
    ) -> list[dict]:
        self.wait_until_store_loaded()

        with self.lock:
            teams = self.teams_by_competition_uuid.get(competition_uuid)
            if teams is not None:
                return copy.deepcopy(teams)

        return self.update(competition_uuid, current_season=current_season)


TEAMS = Teams()
