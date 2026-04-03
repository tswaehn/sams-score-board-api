from __future__ import annotations

import copy

from fetch_competition_list import COMPETITION_LIST_STORE
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

    def update_all(self) -> None:
        matches_by_match_group_uuid: dict[str, dict[str, dict]] = {}
        raw_payload_by_competition_uuid: dict[str, dict] = {}

        for competition in COMPETITION_LIST_STORE.get():
            competition_uuid = competition.get("uuid")
            if not isinstance(competition_uuid, str):
                continue

            payload = fetch_endpoint_direct(f"/competition-matches?for-competition={competition_uuid}")
            if not isinstance(payload, dict):
                raise RuntimeError(
                    f"Expected competition-match list payload to be a dict for {competition_uuid!r}"
                )

            matches = payload.get("content", [])
            if not isinstance(matches, list):
                raise RuntimeError(
                    f"Expected competition-match list content to be a list for {competition_uuid!r}"
                )

            competition_matches_by_match_group_uuid: dict[str, dict[str, dict]] = {}
            for match in matches:
                if not isinstance(match, dict):
                    continue
                match_uuid = match.get("uuid")
                if not isinstance(match_uuid, str):
                    continue

                match_group_uuid = match.get("matchGroupUuid")
                if not isinstance(match_group_uuid, str):
                    continue
                normalized_matches = competition_matches_by_match_group_uuid.setdefault(
                    match_group_uuid,
                    {},
                )
                normalized_matches[match_uuid] = self._normalize_match(match)

            for match_group_uuid, normalized_matches in competition_matches_by_match_group_uuid.items():
                matches_by_match_group_uuid.setdefault(match_group_uuid, {}).update(
                    normalized_matches
                )

            raw_payload_by_competition_uuid[competition_uuid] = payload

        self.dump_raw_json("competition-match-store-raw.json", raw_payload_by_competition_uuid)
        self.replace_store(matches_by_match_group_uuid)

    def get(self, match_group_uuid: str, current_season: bool) -> dict:
        self.wait_until_store_loaded()

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
