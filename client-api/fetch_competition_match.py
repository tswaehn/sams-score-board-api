from __future__ import annotations

import copy

from periodic_updater import PeriodicUpdater
from sams_api_client import extract_uuid_from_url, fetch_endpoint, fetch_endpoint_direct


STORE_TTL_SECONDS = 24 * 60 * 60


class CompetitionMatch(PeriodicUpdater):
    def __init__(self) -> None:
        self.match_uuids_by_match_group_uuid: dict[str, list[str]] = {}
        super().__init__(
            logger_name="competition-api.competition-match",
            thread_name="competition-match-updater",
            store_file_name="competition-match-store.json",
            ttl_seconds=STORE_TTL_SECONDS,
            update_callback=self.updateAll,
        )

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

    def on_store_loaded(self) -> None:
        self.match_uuids_by_match_group_uuid = {}

    def updateAll(self, current_season: bool | None = None) -> list[dict]:
        payload = fetch_endpoint_direct("/competition-matches")
        if not isinstance(payload, dict):
            raise RuntimeError("Expected /competition-matches payload to be a dict")

        matches = payload.get("content", [])
        if not isinstance(matches, list):
            raise RuntimeError("Expected /competition-matches content to be a list")

        normalized_matches = []
        for match in matches:
            if not isinstance(match, dict):
                continue
            match_uuid = match.get("uuid")
            if not isinstance(match_uuid, str):
                continue
            normalized_matches.append(match)

        self.dump_raw_json("competition-match-store-raw.json", payload)
        self.replace_store({
            match["uuid"]: match for match in normalized_matches
        })

        return normalized_matches

    def get(self, match_uuid: str, current_season: bool) -> dict:
        self.wait_until_store_loaded()

        match = self.get_store_item(match_uuid)
        if match is None:
            payload = fetch_endpoint_direct(f"/competition-matches/{match_uuid}")
            if not isinstance(payload, dict):
                raise RuntimeError(f"Expected competition-match payload to be a dict for {match_uuid!r}")
            self.set_store_item(match_uuid, payload)
            match = payload

        return copy.deepcopy(self._normalize_match(match))

    def get_by_match_group_uuid(self, match_group_uuid: str, current_season: bool) -> dict:
        self.wait_until_store_loaded()

        payload = fetch_endpoint(
            f"/match-groups/{match_group_uuid}/competition-matches",
            current_season=current_season,
        )
        if not isinstance(payload, dict):
            raise RuntimeError(
                f"Expected competition-match list payload to be a dict for {match_group_uuid!r}"
            )

        matches = payload.get("content", [])
        if not isinstance(matches, list):
            raise RuntimeError(
                f"Expected competition-match list content to be a list for {match_group_uuid!r}"
            )

        normalized_matches: dict[str, dict] = {}
        match_uuids: list[str] = []
        with self.lock:
            next_store = dict(self.store)
            for match in matches:
                if not isinstance(match, dict):
                    continue
                next_store[match["uuid"]] = match
                match_uuids.append(match["uuid"])
        self.dump_raw_json(
            f"competition-match-store-raw-match-group-{match_group_uuid}.json",
            payload,
        )
        self.replace_store(next_store)
        with self.lock:
            self.match_uuids_by_match_group_uuid[match_group_uuid] = match_uuids

        for match in matches:
            if not isinstance(match, dict):
                continue
            normalized_matches[match["uuid"]] = self._normalize_match(match)

        return normalized_matches


COMPETITION_MATCH = CompetitionMatch()
