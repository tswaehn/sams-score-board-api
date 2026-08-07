from __future__ import annotations

from competition.fetch_competition_list import COMPETITION_LIST_STORE
from competition.fetch_competition_matches import COMPETITION_MATCHES
from periodic_updater import PeriodicUpdater
from sams_api_client import extract_uuid_from_url, fetch_endpoint_direct


STORE_TTL_SECONDS = 60
FINISHED_STORE_TTL_SECONDS = 24 * 60 * 60


class MatchGroup(PeriodicUpdater):
    def __init__(self) -> None:
        super().__init__(
            logger_name="api.match-group",
            thread_name="match-group-updater",
            store_file_name="match-group-store.json",
        )

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
        self.set_store_item(
            uuid,
            normalized_match_groups,
            self._get_ttl_seconds(normalized_match_groups),
        )

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
        matches = COMPETITION_MATCHES.get(match_group_uuid, current_season)
        return {
            "uuid": match_group["uuid"],
            "name": match_group["name"],
            "tourneyLevel": match_group["tourneyLevel"],
            "match_group_uuid": match_group_uuid,
            "finished": self._is_finished(matches),
            "matches": matches,
        }

    def _is_finished(self, matches: dict) -> bool:
        if not isinstance(matches, dict) or not matches:
            return False

        return all(
            isinstance(match, dict) and bool(match.get("finished"))
            for match in matches.values()
        )

    def _get_ttl_seconds(self, match_groups: dict[str, dict]) -> float:
        if match_groups and all(
            isinstance(match_group, dict) and bool(match_group.get("finished"))
            for match_group in match_groups.values()
        ):
            return FINISHED_STORE_TTL_SECONDS
        return STORE_TTL_SECONDS


MATCH_GROUP = MatchGroup()
