from __future__ import annotations

import copy

from periodic_updater import PeriodicUpdater
from sams_api_client import extract_uuid_from_url, fetch_endpoint_direct


STORE_TTL_SECONDS = 60


class LeagueMatches(PeriodicUpdater):
    def __init__(self) -> None:
        super().__init__(
            logger_name="competition-api.league-match",
            thread_name="league-match-updater",
            store_file_name="league-match-store.json",
            ttl_seconds=STORE_TTL_SECONDS,
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
        self.set_store_item(uuid, normalized_matches)

    def get(self, match_day_uuid: str) -> dict:
        self.wait_for_uuid(match_day_uuid)

        matches = self.get_store_item(match_day_uuid)
        if matches is None:
            self.logger.warning("Match day %r not found in league-match store", match_day_uuid)
            return {}

        return copy.deepcopy(matches)

    def _normalize_match(self, match: dict) -> dict:
        team1_link = match.get("_links", {}).get("team1")
        team2_link = match.get("_links", {}).get("team2")
        team1_uuid = extract_uuid_from_url(team1_link["href"]) if team1_link else None
        team2_uuid = extract_uuid_from_url(team2_link["href"]) if team2_link else None
        return {
            "uuid": match["uuid"],
            "date": match["date"].split("T", 1)[0] if isinstance(match.get("date"), str) else None,
            "time": match.get("time"),
            "location": match.get("location"),
            "matchNumber": match.get("matchNumber"),
            "team1_uuid": team1_uuid,
            "team2_uuid": team2_uuid,
            "team1_name": match.get("team1Description"),
            "team2_name": match.get("team2Description"),
            "results": match.get("results"),
        }


LEAGUE_MATCHES = LeagueMatches()

