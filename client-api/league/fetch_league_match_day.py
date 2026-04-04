from __future__ import annotations

from league.fetch_league_matches import LEAGUE_MATCHES
from periodic_updater import PeriodicUpdater
from sams_api_client import fetch_endpoint_direct


STORE_TTL_SECONDS = 60


class LeagueMatchDayStore(PeriodicUpdater):
    def __init__(self) -> None:
        super().__init__(
            logger_name="competition-api.league-match-day",
            thread_name="league-match-day-updater",
            store_file_name="league-match-day-store.json",
            ttl_seconds=STORE_TTL_SECONDS,
        )

    def update_store(self, uuid: str | None = None) -> None:
        if uuid is None:
            return

        payload = fetch_endpoint_direct(f"/leagues/{uuid}/match-days")
        if not isinstance(payload, dict):
            raise RuntimeError(f"Expected league match-day list payload to be a dict for {uuid!r}")

        match_days = payload.get("content", [])
        if not isinstance(match_days, list):
            raise RuntimeError(f"Expected league match-day list content to be a list for {uuid!r}")

        normalized_match_days: dict[str, dict] = {}
        for index, match_day in enumerate(match_days):
            if not isinstance(match_day, dict):
                continue
            normalized = self._normalize_match_day(match_day)
            sort_key = normalized.get("matchdate") or f"9999-{index:04d}"
            normalized["tourneyLevel"] = index
            normalized_match_days[f"{sort_key}:{normalized['uuid']}"] = normalized

        self.dump_raw_json("league-match-day-store-raw.json", uuid, payload)
        self.set_store_item(uuid, normalized_match_days)

    def get(self, league_uuid: str) -> dict:
        self.wait_for_uuid(league_uuid)

        match_days = self.get_store_item(league_uuid)
        if match_days is None:
            raise KeyError(f"League {league_uuid!r} not found in match-day store")

        return {
            match_day["name"]: dict(match_day)
            for match_day in sorted(
                match_days.values(),
                key=lambda item: (item.get("matchdate") or "", item.get("name") or ""),
            )
            if isinstance(match_day, dict)
        }

    def _normalize_match_day(self, match_day: dict) -> dict:
        match_day_uuid = match_day["uuid"]
        matchdate = match_day.get("matchdate")
        matchdate_label = matchdate.split("T", 1)[0] if isinstance(matchdate, str) else "Unknown"
        name = match_day.get("name") or f"Match day {matchdate_label}"
        return {
            "uuid": match_day_uuid,
            "name": name,
            "matchdate": matchdate,
            "matches": LEAGUE_MATCHES.get(match_day_uuid),
        }


LEAGUE_MATCH_DAY_STORE = LeagueMatchDayStore()

