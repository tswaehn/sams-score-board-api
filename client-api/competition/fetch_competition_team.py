from __future__ import annotations

import copy

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

    def update_store(self, uuid: str | None = None) -> None:
        if uuid is None:
            return

        payload = fetch_endpoint_direct(f"/competitions/{uuid}/teams")
        if not isinstance(payload, dict):
            raise RuntimeError(f"Expected teams payload to be a dict for {uuid!r}")

        teams = payload.get("content", [])
        if not isinstance(teams, list):
            raise RuntimeError(f"Expected teams content to be a list for {uuid!r}")

        normalized_teams = []
        for team in teams:
            if not isinstance(team, dict):
                continue
            normalized_teams.append(self._normalize_team(team))

        self.dump_raw_json("competition-teams-store-raw.json", uuid, payload)
        self.set_store_item(uuid, normalized_teams)

    def get(self, competition_uuid: str) -> list[dict]:
        self.wait_for_uuid(competition_uuid)

        teams = self.get_store_item(competition_uuid)
        if teams is not None:
            return copy.deepcopy(teams)

        return []

    def _normalize_team(self, team: dict) -> dict:
        return {
            "uuid": team["uuid"],
            "name": team["name"],
            "shortName": team["shortName"],
            "logoImageLink": team["logoImageLink"],
        }


COMPETITION_TEAMS = CompetitionTeams()

