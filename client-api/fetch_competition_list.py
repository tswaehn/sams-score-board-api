from __future__ import annotations

import copy

from fetch_association import ASSOCIATION
from fetch_season import SEASON
from periodic_updater import PeriodicUpdater
from sams_api_client import extract_endpoint_from_url, extract_uuid_from_url, fetch_endpoint_direct


STORE_TTL_SECONDS = 24 * 60 * 60


class CompetitionListStore(PeriodicUpdater):
    def __init__(self) -> None:
        self.competition_uuids_by_season: dict[str, set[str]] = {}
        super().__init__(
            logger_name="competition-api.competition-list",
            thread_name="competition-list-updater",
            store_file_name="competition-list-store.json",
            ttl_seconds=STORE_TTL_SECONDS,
        )

    def on_store_loaded(self) -> None:
        season_map: dict[str, set[str]] = {}
        for competition_uuid, competition in self.store.items():
            if not isinstance(competition, dict):
                continue
            season = competition.get("season")
            if not isinstance(season, dict):
                continue
            season_uuid = season.get("uuid")
            if not isinstance(season_uuid, str):
                continue
            season_map.setdefault(season_uuid, set()).add(competition_uuid)

        self.competition_uuids_by_season = season_map

    def update_all(self) -> None:
        SEASON.update_all()
        seasons_payload = SEASON.get_all()

        for season in seasons_payload:
            season_uuid = season.get("uuid")
            if not isinstance(season_uuid, str):
                continue
            self.update_competition_list_by_season(season_uuid)

    def get(self) -> list[dict]:
        self.wait_until_store_loaded()

        with self.lock:
            return [copy.deepcopy(competition) for competition in self.store.values()]

    def update_competition_list_by_season(self, season_uuid: str) -> None:
        season_payload = self.get_season_payload(season_uuid)
        competitions_payload = fetch_endpoint_direct(f"/competitions?season={season_uuid}")
        if not isinstance(competitions_payload, dict):
            raise RuntimeError(f"Expected competition list payload to be a dict for season {season_uuid!r}")

        competitions = competitions_payload.get("content", [])
        if not isinstance(competitions, list):
            raise RuntimeError(f"Expected competition list content to be a list for season {season_uuid!r}")

        season_competitions = [
            self.build_competition_entry(competition, season_payload)
            for competition in competitions
        ]
        self.store_competitions_for_season(season_uuid, season_competitions, competitions_payload)

    def get_season_payload(self, season_uuid: str) -> dict:
        payload = SEASON.get(season_uuid)
        if not isinstance(payload, dict):
            raise RuntimeError(f"Expected season payload to be a dict for {season_uuid!r}")
        return payload

    def build_competition_entry(
        self,
        competition: dict,
        season_payload: dict,
    ) -> dict:
        association_uuid = extract_uuid_from_url(competition["_links"]["association"]["href"])
        association_url = extract_endpoint_from_url(competition["_links"]["association"]["href"])
        current_season = bool(season_payload.get("currentSeason"))
        association = ASSOCIATION.get(association_uuid)

        return {
            "uuid": competition["uuid"],
            "name": competition["name"],
            "gender": competition["gender"],
            "shortname": competition["shortName"],
            "currentSeason": current_season,
            "association_url": association_url,
            "season_url": f"seasons/{season_payload['uuid']}",
            "association": {
                "uuid": association["uuid"],
                "name": association["name"],
                "shortname": association["shortname"],
            },
            "season": {
                "uuid": season_payload["uuid"],
                "name": season_payload["name"],
            },
        }

    def store_competitions_for_season(
        self,
        season_uuid: str,
        competition_list: list[dict],
        raw_payload: dict,
    ) -> None:
        updated_competitions = self.verify_competition_list(competition_list)
        updated_competition_ids = {competition["uuid"] for competition in updated_competitions}

        with self.lock:
            next_store = dict(self.store)
            previous_competition_ids = self.competition_uuids_by_season.get(season_uuid, set())
            for competition_uuid in previous_competition_ids - updated_competition_ids:
                next_store.pop(competition_uuid, None)

            for competition in updated_competitions:
                next_store[competition["uuid"]] = competition

        self.dump_raw_json(
            f"competition-list-store-raw-season-{season_uuid}.json",
            raw_payload,
        )
        self.replace_store(next_store)

    def verify_competition_list(self, competition_list: list[dict]) -> list[dict]:
        verified_competitions = []
        seen_uuids = set()

        for competition in competition_list:
            competition_uuid = competition["uuid"]
            if competition_uuid in seen_uuids:
                continue

            seen_uuids.add(competition_uuid)
            verified_competitions.append(competition)

        return verified_competitions


COMPETITION_LIST_STORE = CompetitionListStore()


def update_competition_list_by_season(season_uuid: str) -> None:
    COMPETITION_LIST_STORE.update_competition_list_by_season(season_uuid)


def update_all() -> None:
    COMPETITION_LIST_STORE.update_all()


def get_competition_list() -> list[dict]:
    return COMPETITION_LIST_STORE.get()
