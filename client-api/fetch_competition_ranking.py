from __future__ import annotations

import copy

from fetch_competition_list import COMPETITION_LIST_STORE
from periodic_updater import PeriodicUpdater
from sams_api_client import fetch_endpoint


STORE_TTL_SECONDS = 24 * 60 * 60


class CompetitionRanking(PeriodicUpdater):
    def __init__(self) -> None:
        super().__init__(
            logger_name="competition-api.competition-ranking",
            thread_name="competition-ranking-updater",
            store_file_name="competition-ranking-store.json",
            ttl_seconds=STORE_TTL_SECONDS,
        )

    def update_all(self) -> None:
        COMPETITION_LIST_STORE.wait_until_store_loaded()

        next_store: dict[str, dict] = {}
        for competition in COMPETITION_LIST_STORE.get():
            competition_uuid = competition.get("uuid")
            if not isinstance(competition_uuid, str):
                continue
            next_store[competition_uuid] = self.get_rankings(
                competition_uuid,
                current_season=bool(competition.get("currentSeason")),
            )

        self.replace_store(next_store)

    def get(self, competition_uuid: str, current_season: bool) -> dict:
        self.wait_until_store_loaded()

        rankings = self.get_store_item(competition_uuid)
        if rankings is not None:
            return copy.deepcopy(rankings)

        return self.get_rankings(competition_uuid, current_season)

    def get_rankings(self, competition_uuid: str, current_season: bool) -> dict:
        rankings_payload = fetch_endpoint(
            f"/competitions/{competition_uuid}/rankings",
            current_season=current_season,
        )
        if not isinstance(rankings_payload, dict):
            raise RuntimeError(f"Expected rankings payload to be a dict for {competition_uuid!r}")

        rankings = rankings_payload.get("content", [])
        if not isinstance(rankings, list):
            raise RuntimeError(f"Expected rankings content to be a list for {competition_uuid!r}")

        normalized_rankings = self._normalize_rankings(rankings)
        self.dump_raw_json(
            f"competition-ranking-store-raw-competition-{competition_uuid}.json",
            rankings_payload,
        )
        self.set_store_item(competition_uuid, normalized_rankings)
        return copy.deepcopy(normalized_rankings)

    def _normalize_rankings(self, rankings: list[dict]) -> dict:
        result: dict[str, dict] = {}

        for ranking in rankings:
            if not isinstance(ranking, dict):
                continue

            match_group_name = ranking.get("matchGroupName")
            if not isinstance(match_group_name, str):
                continue

            normalized_ranking: dict[int | str, dict] = {}
            for entry in ranking.get("rankings", []):
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
                }

            result[match_group_name] = normalized_ranking

        return result


COMPETITION_RANKING = CompetitionRanking()
