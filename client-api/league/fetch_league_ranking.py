from __future__ import annotations

import copy

from periodic_updater import PeriodicUpdater
from sams_api_client import fetch_endpoint_direct


STORE_TTL_SECONDS = 60


class LeagueRanking(PeriodicUpdater):
    def __init__(self) -> None:
        super().__init__(
            logger_name="competition-api.league-ranking",
            thread_name="league-ranking-updater",
            store_file_name="league-ranking-store.json",
            ttl_seconds=STORE_TTL_SECONDS,
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
        self.set_store_item(uuid, normalized_rankings)

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
            normalized_ranking[rank] = {
                "teamName": entry["teamName"],
                "matchesPlayed": entry["matchesPlayed"],
                "wins": entry["wins"],
                "losses": entry["losses"],
                "setWins": entry["setWins"],
                "setLosses": entry["setLosses"],
                "ballWins": entry["ballWins"],
                "ballLosses": entry["ballLosses"],
                "ballDifference": entry["ballDifference"],
                "points": entry.get("points"),
            }

        return {"Table": normalized_ranking}


LEAGUE_RANKING = LeagueRanking()

