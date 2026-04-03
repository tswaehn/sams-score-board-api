from __future__ import annotations

import copy
import threading
import time
from datetime import datetime, timedelta

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
        self.update_all_thread = threading.Thread(
            target=self.run_update_all_loop,
            name="competition-list-update-all",
            daemon=True,
        )
        self.update_all_thread.start()

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

    def update_store(self, uuid: str | None = None) -> None:
        if uuid is None:
            self.update_all()
            return

        self._update_store(uuid)

    def update_all(self) -> None:
        seasons = SEASON.get_all()

        for season in seasons:
            if not isinstance(season, dict):
                continue

            season_uuid = season.get("uuid")
            if not isinstance(season_uuid, str):
                continue

            # if not season.get("currentSeason"):
            #    continue

            competitions_payload = fetch_endpoint_direct(f"/competitions?season={season_uuid}")
            if not isinstance(competitions_payload, dict):
                raise RuntimeError(
                    f"Expected competition list payload to be a dict for season {season_uuid!r}"
                )

            competitions = competitions_payload.get("content", [])
            if not isinstance(competitions, list):
                raise RuntimeError(
                    f"Expected competition list content to be a list for season {season_uuid!r}"
                )

            for competition in competitions:
                if not isinstance(competition, dict):
                    continue

                competition_uuid = competition.get("uuid")
                if not isinstance(competition_uuid, str):
                    continue
                self._update_store(competition_uuid, competition)

    def seconds_until_next_update_all(self) -> float:
        now = datetime.now()
        next_update = now.replace(hour=1, minute=0, second=0, microsecond=0)
        if now >= next_update:
            next_update = next_update + timedelta(days=1)
        return max((next_update - now).total_seconds(), 0.0)

    def should_update_all_on_startup(self) -> bool:
        with self.lock:
            if not self.store:
                return True
            return self.is_store_expired()

    def run_update_all_loop(self) -> None:
        if self.should_update_all_on_startup():
            try:
                self.update_all()
            except Exception:
                self.logger.exception("Competition list startup update_all failed")

        while True:
            sleep_seconds = self.seconds_until_next_update_all()
            time.sleep(sleep_seconds)
            try:
                self.update_all()
            except Exception:
                self.logger.exception("Competition list scheduled update_all failed")

    def get(self) -> list[dict]:
        self.wait_for_uuid()

        with self.lock:
            return [copy.deepcopy(competition) for competition in self.store.values()]

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

    def _update_store(self, uuid: str, competition_payload: dict | None = None) -> None:
        if competition_payload is None:
            competition_payload = fetch_endpoint_direct(f"/competitions/{uuid}")
            if not isinstance(competition_payload, dict):
                raise RuntimeError(f"Expected competition payload to be a dict for {uuid!r}")

        season_uuid = extract_uuid_from_url(competition_payload["_links"]["season"]["href"])
        season_payload = SEASON.get(season_uuid)
        competition_entry = self.build_competition_entry(competition_payload, season_payload)

        self.dump_raw_json("competition-list-store-raw.json", uuid, competition_payload)
        self.set_store_item(uuid, competition_entry)

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
