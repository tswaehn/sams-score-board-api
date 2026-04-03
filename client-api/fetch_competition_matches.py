from __future__ import annotations

import copy

from periodic_updater import PeriodicUpdater
from sams_api_client import extract_uuid_from_url, fetch_endpoint_direct


STORE_TTL_SECONDS = 24 * 60 * 60


class CompetitionMatches(PeriodicUpdater):
    def __init__(self) -> None:
        super().__init__(
            logger_name="competition-api.competition-match",
            thread_name="competition-match-updater",
            store_file_name="competition-match-store.json",
            ttl_seconds=STORE_TTL_SECONDS,
        )

    def update_store(self, uuid: str | None = None) -> None:
        if uuid is None:
            return

        payload = fetch_endpoint_direct(f"/match-groups/{uuid}/competition-matches")
        if not isinstance(payload, dict):
            raise RuntimeError(
                f"Expected competition-match list payload to be a dict for {uuid!r}"
            )

        matches = payload.get("content", [])
        if not isinstance(matches, list):
            raise RuntimeError(
                f"Expected competition-match list content to be a list for {uuid!r}"
            )

        normalized_matches: dict[str, dict] = {}
        for match in matches:
            if not isinstance(match, dict):
                continue
            match_uuid = match.get("uuid")
            if not isinstance(match_uuid, str):
                continue
            normalized_matches[match_uuid] = self._normalize_match(match)

        self.dump_raw_json("competition-match-store-raw.json", uuid, payload)
        self.set_store_item(uuid, normalized_matches)

    def get(self, match_group_uuid: str, current_season: bool) -> dict:
        self.wait_for_uuid(match_group_uuid)

        matches = self.get_store_item(match_group_uuid)
        if matches is None:
            self.logger.warning(
                "Match group %r not found in competition-match store",
                match_group_uuid,
            )
            return {}

        return copy.deepcopy(matches)

    def _normalize_match(self, match: dict) -> dict:
        team1_link = match["_links"].get("team1")
        team2_link = match["_links"].get("team2")
        team1_uuid = extract_uuid_from_url(team1_link["href"]) if team1_link else None
        team2_uuid = extract_uuid_from_url(team2_link["href"]) if team2_link else None
        return {
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


COMPETITION_MATCHES = CompetitionMatches()
