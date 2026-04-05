from __future__ import annotations

import copy

from periodic_updater import PeriodicUpdater
from sams_api_client import fetch_endpoint_direct
from shared.entity_utils import normalize_team


STORE_TTL_SECONDS = 24 * 60 * 60


class Teams(PeriodicUpdater):
    def __init__(self) -> None:
        super().__init__(
            logger_name="competition-api.teams",
            thread_name="teams-updater",
            store_file_name="teams-store.json",
            ttl_seconds=STORE_TTL_SECONDS,
        )

    def update_store(self, uuid: str | None = None) -> None:
        if uuid is None:
            return

        payload = fetch_endpoint_direct(f"/teams/{uuid}")
        if not isinstance(payload, dict):
            raise RuntimeError(f"Expected team payload to be a dict for {uuid!r}")

        team = self._normalize_team(payload)
        self.dump_raw_json("teams-store-raw.json", uuid, team)
        self.set_store_item(uuid, team)

    def get(self, team_uuid: str) -> dict:
        self.wait_for_uuid(team_uuid)

        team = self.get_store_item(team_uuid)
        if team is not None:
            return copy.deepcopy(team)

        payload = fetch_endpoint_direct(f"/teams/{team_uuid}")
        if not isinstance(payload, dict):
            raise RuntimeError(f"Expected team payload to be a dict for {team_uuid!r}")

        team = self._normalize_team(payload)
        self.set_store_item(team_uuid, team)
        return copy.deepcopy(team)

    def _normalize_team(self, team: dict) -> dict:
        return normalize_team(team)

    def _extract_normalized_teams(self, payload: dict, context: str) -> list[dict]:
        teams = payload.get("content", [])
        if not isinstance(teams, list):
            raise RuntimeError(f"Expected teams content to be a list for {context}")

        normalized_teams = []
        for team in teams:
            if not isinstance(team, dict):
                continue
            normalized_teams.append(self._normalize_team(team))

        return normalized_teams


TEAMS = Teams()
