from __future__ import annotations

from fetch_competition_list import COMPETITION_LIST_STORE
from fetch_competition_matches import COMPETITION_MATCHES
from periodic_updater import PeriodicUpdater
from sams_api_client import extract_uuid_from_url, fetch_endpoint_direct


STORE_TTL_SECONDS = 60


class MatchGroup(PeriodicUpdater):
    def __init__(self) -> None:
        super().__init__(
            logger_name="competition-api.match-group",
            thread_name="match-group-updater",
            store_file_name="match-group-store.json",
            ttl_seconds=STORE_TTL_SECONDS,
        )

    def on_store_loaded(self) -> None:
        pass

    def update_store(self, uuid: str | None = None) -> None:
        if uuid is None:
            return

        competition_entry = COMPETITION_LIST_STORE.get_store_item(uuid)
        current_season = bool(competition_entry.get("currentSeason")) if isinstance(competition_entry, dict) else False
        payload = fetch_endpoint_direct(f"/competitions/{uuid}/match-groups")
        if not isinstance(payload, dict):
            raise RuntimeError(
                f"Expected match-group list payload to be a dict for {uuid!r}"
            )

        match_groups = payload.get("content", [])
        if not isinstance(match_groups, list):
            raise RuntimeError(
                f"Expected match-group list content to be a list for {uuid!r}"
            )

        normalized_match_groups: dict[str, dict] = {}
        for match_group in match_groups:
            if not isinstance(match_group, dict):
                continue
            normalized_match_groups[match_group["name"]] = self._normalize_match_group(
                match_group,
                current_season,
            )

        self.dump_raw_json("match-group-store-raw.json", uuid, payload)
        self.set_store_item(uuid, normalized_match_groups)

    def get(self, competition_uuid: str, current_season: bool) -> dict:
        self.wait_for_uuid(competition_uuid)

        normalized_match_groups = self.get_store_item(competition_uuid)
        if normalized_match_groups is None:
            raise KeyError(f"Competition {competition_uuid!r} not found in match-group store")

        return {
            name: dict(match_group) if isinstance(match_group, dict) else match_group
            for name, match_group in normalized_match_groups.items()
        }

    def _normalize_match_group(self, match_group: dict, current_season: bool) -> dict:
        match_group_uuid = extract_uuid_from_url(match_group["_links"]["matches"]["href"])
        return {
            "uuid": match_group["uuid"],
            "name": match_group["name"],
            "tourneyLevel": match_group["tourneyLevel"],
            "match_group_uuid": match_group_uuid,
            "matches": COMPETITION_MATCHES.get(match_group_uuid, current_season),
        }


MATCH_GROUP = MatchGroup()
