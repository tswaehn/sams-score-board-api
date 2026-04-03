from __future__ import annotations

import copy

from fetch_competition_list import COMPETITION_LIST_STORE
from periodic_updater import PeriodicUpdater
from sams_api_client import fetch_endpoint_direct


STORE_TTL_SECONDS = 24 * 60 * 60


class CompetitionTeams(PeriodicUpdater):
    def __init__(self) -> None:
        super().__init__(
            logger_name="competition-api.competition-teams",
            thread_name="competition-teams-updater",
            store_file_name="competition-teams-store.json",
            ttl_seconds=STORE_TTL_SECONDS,
        )

    def update_all(self) -> None:
        COMPETITION_LIST_STORE.wait_until_store_loaded()

        next_store: dict[str, list[dict]] = {}
        for competition in COMPETITION_LIST_STORE.get():
            competition_uuid = competition.get("uuid")
            if not isinstance(competition_uuid, str):
                continue

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

            self.dump_raw_json(
                f"competition-teams-store-raw-competition-{competition_uuid}.json",
                payload,
            )
            next_store[competition_uuid] = normalized_teams

        self.replace_store(next_store)

    def get(self, competition_uuid: str) -> list[dict]:
        self.wait_until_store_loaded()

        teams = self.get_store_item(competition_uuid)
        if teams is not None:
            return copy.deepcopy(teams)

        payload, teams = self._fetch_teams_for_competition(competition_uuid)
        self.dump_raw_json(
            f"competition-teams-store-raw-competition-{competition_uuid}.json",
            payload,
        )
        self.set_store_item(competition_uuid, teams)
        return copy.deepcopy(teams)

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


COMPETITION_TEAMS = CompetitionTeams()
