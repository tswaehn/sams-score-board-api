from __future__ import annotations

import copy
import threading
import time

from periodic_updater import PeriodicUpdater
from sams_api_client import extract_uuid_from_url, fetch_endpoint_direct
from shared.entity_utils import build_entry_from_linked_payload, seconds_until_daily_update
from shared.fetch_season import SEASON


STORE_TTL_SECONDS = 24 * 60 * 60


class CompetitionListStore(PeriodicUpdater):
    def __init__(self) -> None:
        self.competition_uuids_by_season: dict[str, set[str]] = {}
        super().__init__(
            logger_name="api.competition-list",
            thread_name="competition-list-updater",
            store_file_name="competition-list-store.json",
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
        competitions_payload = fetch_endpoint_direct("/competitions")
        if not isinstance(competitions_payload, dict):
            raise RuntimeError("Expected competition list payload to be a dict")

        competitions = competitions_payload.get("content", [])
        if not isinstance(competitions, list):
            raise RuntimeError("Expected competition list content to be a list")

        next_store: dict[str, dict] = {}
        raw_payload: dict[str, dict] = {}

        for competition in competitions:
            if not isinstance(competition, dict):
                continue

            competition_uuid = competition.get("uuid")
            if not isinstance(competition_uuid, str):
                continue
            next_store[competition_uuid] = self.build_competition_entry_from_payload(competition)
            raw_payload[competition_uuid] = competition

        self.dump_raw_store("competition-list-store-raw.json", raw_payload)
        self.replace_store(next_store, STORE_TTL_SECONDS)

    def seconds_until_next_update_all(self) -> float:
        return seconds_until_daily_update(1, 0)

    def should_update_all_on_startup(self) -> bool:
        with self.lock:
            if not self.store:
                return True
            return self.is_store_expired()

    def run_update_all_loop(self) -> None:
        if self.should_update_all_on_startup():
            try:
                self._run_coalesced_update()
            except Exception:
                self.logger.exception("Competition list startup update_all failed")

        while True:
            sleep_seconds = self.seconds_until_next_update_all()
            time.sleep(sleep_seconds)
            try:
                self._run_coalesced_update()
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
        entry = build_entry_from_linked_payload(
            entity_type="competition",
            payload=competition,
            association_link=competition["_links"]["association"]["href"],
            season_link=competition["_links"]["season"]["href"],
        )
        entry["currentSeason"] = bool(season_payload.get("currentSeason"))
        return entry

    def build_competition_entry_from_payload(self, competition_payload: dict) -> dict:
        season_uuid = extract_uuid_from_url(competition_payload["_links"]["season"]["href"])
        season_payload = SEASON.get(season_uuid)
        return self.build_competition_entry(competition_payload, season_payload)

    def _update_store(self, uuid: str, competition_payload: dict | None = None) -> None:
        if competition_payload is None:
            competition_payload = fetch_endpoint_direct(f"/competitions/{uuid}")
            if not isinstance(competition_payload, dict):
                raise RuntimeError(f"Expected competition payload to be a dict for {uuid!r}")

        competition_entry = self.build_competition_entry_from_payload(competition_payload)

        self.dump_raw_json("competition-list-store-raw.json", uuid, competition_payload)
        self.set_store_item(uuid, competition_entry, STORE_TTL_SECONDS)


COMPETITION_LIST_STORE = CompetitionListStore()
