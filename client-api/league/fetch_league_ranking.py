from __future__ import annotations

import copy

from league.fetch_league_match_day import LEAGUE_MATCH_DAY_STORE
from periodic_updater import PeriodicUpdater
from sams_api_client import fetch_endpoint_direct
from shared.entity_utils import normalize_ranking_entry


STORE_TTL_SECONDS = 60
FINISHED_STORE_TTL_SECONDS = 24 * 60 * 60


class LeagueRanking(PeriodicUpdater):
    def __init__(self) -> None:
        super().__init__(
            logger_name="api.league-ranking",
            thread_name="league-ranking-updater",
            store_file_name="league-ranking-store.json",
        )

    def update_store(self, uuid: str | None = None) -> None:
        if uuid is None:
            return

        rankings_payload = fetch_endpoint_direct(f"/leagues/{uuid}/rankings")
        if not isinstance(rankings_payload, dict):
            raise RuntimeError(f"Expected rankings payload to be a dict for {uuid!r}")

        rankings = rankings_payload.get("content", [])
        if not isinstance(rankings, list):
            raise RuntimeError(f"Expected rankings content to be a list for {uuid!r}")

        normalized_rankings = self._normalize_rankings(rankings)
        self.dump_raw_json("league-ranking-store-raw.json", uuid, rankings_payload)
        self.set_store_item(
            uuid,
            normalized_rankings,
            self._get_ttl_seconds(uuid, normalized_rankings),
        )

    def get(self, league_uuid: str) -> dict:
        self.wait_for_uuid(league_uuid)

        rankings = self.get_store_item(league_uuid)
        if rankings is None:
            raise KeyError(f"League {league_uuid!r} not found in ranking store")
        return copy.deepcopy(rankings)

    def _normalize_rankings(self, rankings: list[dict]) -> dict:
        normalized_ranking: dict[int | str, dict] = {}

        for entry in rankings:
            if not isinstance(entry, dict):
                continue
            rank = entry.get("rank")
            normalized_ranking[rank] = normalize_ranking_entry(entry, include_points=True)

        return {"Table": normalized_ranking}

    def _get_ttl_seconds(self, league_uuid: str, rankings: dict[str, dict]) -> float:
        if not rankings:
            return STORE_TTL_SECONDS

        match_days = LEAGUE_MATCH_DAY_STORE.get_store_item(league_uuid)
        if isinstance(match_days, dict) and match_days and all(
            isinstance(match_day, dict) and bool(match_day.get("finished"))
            for match_day in match_days.values()
        ):
            return FINISHED_STORE_TTL_SECONDS
        return STORE_TTL_SECONDS


LEAGUE_RANKING = LeagueRanking()
