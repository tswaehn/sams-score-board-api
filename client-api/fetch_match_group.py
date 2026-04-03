from __future__ import annotations

import copy

from fetch_competition_match import COMPETITION_MATCH
from periodic_updater import PeriodicUpdater
from sams_api_client import extract_uuid_from_url, fetch_endpoint, fetch_endpoint_direct


STORE_TTL_SECONDS = 24 * 60 * 60


class MatchGroup(PeriodicUpdater):
    def __init__(self) -> None:
        self.match_group_uuids_by_competition_uuid: dict[str, list[str]] = {}
        super().__init__(
            logger_name="competition-api.match-group",
            thread_name="match-group-updater",
            store_file_name="match-group-store.json",
            ttl_seconds=STORE_TTL_SECONDS,
        )

    def on_store_loaded(self) -> None:
        self.match_group_uuids_by_competition_uuid = {}

    def update_all(self) -> None:
        payload = fetch_endpoint_direct("/match-groups")
        if not isinstance(payload, dict):
            raise RuntimeError("Expected /match-groups payload to be a dict")

        match_groups = payload.get("content", [])
        if not isinstance(match_groups, list):
            raise RuntimeError("Expected /match-groups content to be a list")

        normalized_match_groups = []
        for match_group in match_groups:
            if not isinstance(match_group, dict):
                continue
            match_group_uuid = match_group.get("uuid")
            if not isinstance(match_group_uuid, str):
                continue
            normalized_match_groups.append(match_group)

        self.dump_raw_json("match-group-store-raw.json", payload)
        self.replace_store({
            match_group["uuid"]: match_group for match_group in normalized_match_groups
        })

    def get(self, match_group_uuid: str, current_season: bool) -> dict:
        self.wait_until_store_loaded()

        match_group = self.get_store_item(match_group_uuid)
        if match_group is None:
            payload = fetch_endpoint_direct(f"/match-groups/{match_group_uuid}")
            if not isinstance(payload, dict):
                raise RuntimeError(f"Expected match-group payload to be a dict for {match_group_uuid!r}")
            self.set_store_item(match_group_uuid, payload)
            match_group = payload

        return copy.deepcopy(self._normalize_match_group(match_group, current_season))

    def get_by_competition_uuid(self, competition_uuid: str, current_season: bool) -> dict:
        self.wait_until_store_loaded()

        payload = fetch_endpoint(
            f"/competitions/{competition_uuid}/match-groups",
            current_season=current_season,
        )
        if not isinstance(payload, dict):
            raise RuntimeError(f"Expected match-group list payload to be a dict for {competition_uuid!r}")

        match_groups = payload.get("content", [])
        if not isinstance(match_groups, list):
            raise RuntimeError(f"Expected match-group list content to be a list for {competition_uuid!r}")

        normalized_match_groups: dict[str, dict] = {}
        match_group_uuids: list[str] = []
        with self.lock:
            next_store = dict(self.store)
            for match_group in match_groups:
                if not isinstance(match_group, dict):
                    continue
                next_store[match_group["uuid"]] = match_group
                match_group_uuids.append(match_group["uuid"])
        self.dump_raw_json(
            f"match-group-store-raw-competition-{competition_uuid}.json",
            payload,
        )
        self.replace_store(next_store)
        with self.lock:
            self.match_group_uuids_by_competition_uuid[competition_uuid] = match_group_uuids

        for match_group in match_groups:
            if not isinstance(match_group, dict):
                continue
            normalized_match_groups[match_group["name"]] = self._normalize_match_group(
                match_group,
                current_season,
            )

        return normalized_match_groups

    def _normalize_match_group(self, match_group: dict, current_season: bool) -> dict:
        matches_uuid = extract_uuid_from_url(match_group["_links"]["matches"]["href"])
        return {
            "uuid": match_group["uuid"],
            "name": match_group["name"],
            "tourneyLevel": match_group["tourneyLevel"],
            "matches_uuid": matches_uuid,
            "matches": COMPETITION_MATCH.get_by_match_group_uuid(matches_uuid, current_season),
        }


MATCH_GROUP = MatchGroup()
