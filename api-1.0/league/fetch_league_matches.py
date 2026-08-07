from __future__ import annotations

import copy

from periodic_updater import PeriodicUpdater
from sams_api_client import fetch_endpoint_direct
from shared.entity_utils import normalize_match


STORE_TTL_SECONDS = 60
FINISHED_STORE_TTL_SECONDS = 24 * 60 * 60


class LeagueMatches(PeriodicUpdater):
    def __init__(self) -> None:
        super().__init__(
            logger_name="api.league-match",
            thread_name="league-match-updater",
            store_file_name="league-match-store.json",
        )

    def update_store(self, uuid: str | None = None) -> None:
        if uuid is None:
            return

        payload = fetch_endpoint_direct(f"/match-days/{uuid}/league-matches")
        if not isinstance(payload, dict):
            raise RuntimeError(f"Expected league-match list payload to be a dict for {uuid!r}")

        matches = payload.get("content", [])
        if not isinstance(matches, list):
            raise RuntimeError(f"Expected league-match list content to be a list for {uuid!r}")

        normalized_matches: dict[str, dict] = {}
        for match in matches:
            if not isinstance(match, dict):
                continue
            match_uuid = match.get("uuid")
            if not isinstance(match_uuid, str):
                continue
            normalized_matches[match_uuid] = self._normalize_match(match)

        self.dump_raw_json("league-match-store-raw.json", uuid, payload)
        self.set_store_item(
            uuid,
            normalized_matches,
            self._get_ttl_seconds(normalized_matches),
        )

    def get(self, match_day_uuid: str) -> dict:
        self.wait_for_uuid(match_day_uuid)

        matches = self.get_store_item(match_day_uuid)
        if matches is None:
            self.logger.warning("Match day %r not found in league-match store", match_day_uuid)
            return {}

        return copy.deepcopy(matches)

    def _normalize_match(self, match: dict) -> dict:
        return normalize_match(match, split_date=True)

    def _get_ttl_seconds(self, matches: dict[str, dict]) -> float:
        if matches and all(
            isinstance(match, dict) and bool(match.get("finished"))
            for match in matches.values()
        ):
            return FINISHED_STORE_TTL_SECONDS
        return STORE_TTL_SECONDS


LEAGUE_MATCHES = LeagueMatches()
