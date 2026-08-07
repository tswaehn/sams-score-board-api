from __future__ import annotations

import copy

from competition.fetch_competition_match_group import MATCH_GROUP
from periodic_updater import PeriodicUpdater
from sams_api_client import fetch_endpoint_direct
from shared.entity_utils import normalize_ranking_entry


STORE_TTL_SECONDS = 60
FINISHED_STORE_TTL_SECONDS = 24 * 60 * 60


class CompetitionRanking(PeriodicUpdater):
    def __init__(self) -> None:
        super().__init__(
            logger_name="api.competition-ranking",
            thread_name="competition-ranking-updater",
            store_file_name="competition-ranking-store.json",
        )

    def update_store(self, uuid: str | None = None) -> None:
        if uuid is None:
            return

        rankings_payload = fetch_endpoint_direct(f"/competitions/{uuid}/rankings")
        if not isinstance(rankings_payload, dict):
            raise RuntimeError(f"Expected rankings payload to be a dict for {uuid!r}")

        rankings = rankings_payload.get("content", [])
        if not isinstance(rankings, list):
            raise RuntimeError(f"Expected rankings content to be a list for {uuid!r}")

        normalized_rankings = self._normalize_rankings(rankings)
        self.dump_raw_json(
            "competition-ranking-store-raw.json",
            uuid,
            rankings_payload,
        )
        self.set_store_item(
            uuid,
            normalized_rankings,
            self._get_ttl_seconds(uuid, normalized_rankings),
        )

    def get(self, competition_uuid: str, current_season: bool) -> dict:
        self.wait_for_uuid(competition_uuid)

        rankings = self.get_store_item(competition_uuid)
        if rankings is None:
            raise KeyError(f"Competition {competition_uuid!r} not found in ranking store")
        return copy.deepcopy(rankings)

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
                normalized_ranking[rank] = normalize_ranking_entry(entry)

            result[match_group_name] = normalized_ranking

        return result

    def _get_ttl_seconds(self, competition_uuid: str, rankings: dict[str, dict]) -> float:
        if not rankings:
            return STORE_TTL_SECONDS

        match_groups = MATCH_GROUP.get_store_item(competition_uuid)
        if isinstance(match_groups, dict) and match_groups and all(
            isinstance(match_group, dict) and bool(match_group.get("finished"))
            for match_group in match_groups.values()
        ):
            return FINISHED_STORE_TTL_SECONDS
        return STORE_TTL_SECONDS


COMPETITION_RANKING = CompetitionRanking()
