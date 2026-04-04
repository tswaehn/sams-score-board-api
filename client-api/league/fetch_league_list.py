from __future__ import annotations

import copy
import threading
import time
from datetime import datetime, timedelta

from fetch_association import ASSOCIATION
from fetch_season import SEASON
from periodic_updater import PeriodicUpdater
from sams_api_client import fetch_endpoint_direct


STORE_TTL_SECONDS = 24 * 60 * 60


class LeagueListStore(PeriodicUpdater):
    def __init__(self) -> None:
        super().__init__(
            logger_name="competition-api.league-list",
            thread_name="league-list-updater",
            store_file_name="league-list-store.json",
            ttl_seconds=STORE_TTL_SECONDS,
        )
        self.update_all_thread = threading.Thread(
            target=self.run_update_all_loop,
            name="league-list-update-all",
            daemon=True,
        )
        self.update_all_thread.start()

    def update_store(self, uuid: str | None = None) -> None:
        if uuid is None:
            self.update_all()
            return

        self._update_store(uuid)

    def update_all(self) -> None:
        leagues_payload = fetch_endpoint_direct("/leagues")
        if not isinstance(leagues_payload, dict):
            raise RuntimeError("Expected league list payload to be a dict")

        leagues = leagues_payload.get("content", [])
        if not isinstance(leagues, list):
            raise RuntimeError("Expected league list content to be a list")

        next_store: dict[str, dict] = {}
        raw_payload: dict[str, dict] = {}

        for league in leagues:
            if not isinstance(league, dict):
                continue

            league_uuid = league.get("uuid")
            if not isinstance(league_uuid, str):
                continue
            next_store[league_uuid] = self.build_league_entry(league)
            raw_payload[league_uuid] = league

        raw_file_path = self.store_file_path.parent / "league-list-store-raw.json"
        self._write_json_file(raw_file_path, raw_payload)
        self.replace_store(next_store)

    def seconds_until_next_update_all(self) -> float:
        now = datetime.now()
        next_update = now.replace(hour=1, minute=15, second=0, microsecond=0)
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
                self._run_coalesced_update()
            except Exception:
                self.logger.exception("League list startup update_all failed")

        while True:
            time.sleep(self.seconds_until_next_update_all())
            try:
                self._run_coalesced_update()
            except Exception:
                self.logger.exception("League list scheduled update_all failed")

    def get(self) -> list[dict]:
        self.wait_for_uuid()

        with self.lock:
            return [copy.deepcopy(league) for league in self.store.values()]

    def build_league_entry(self, league: dict) -> dict:
        association_uuid = league.get("associationUuid")
        season_uuid = league.get("seasonUuid")
        association = ASSOCIATION.get(association_uuid) if isinstance(association_uuid, str) else {}
        season = SEASON.get(season_uuid) if isinstance(season_uuid, str) else {}
        current_season = bool(season.get("currentSeason"))

        return {
            "uuid": league["uuid"],
            "entityType": "league",
            "name": league["name"],
            "gender": league["gender"],
            "shortname": league["shortName"],
            "currentSeason": current_season,
            "association": {
                "uuid": association.get("uuid"),
                "name": association.get("name"),
                "shortname": association.get("shortname"),
            },
            "season": {
                "uuid": season.get("uuid"),
                "name": season.get("name"),
            },
        }

    def _update_store(self, uuid: str, league_payload: dict | None = None) -> None:
        if league_payload is None:
            league_payload = fetch_endpoint_direct(f"/leagues/{uuid}")
            if not isinstance(league_payload, dict):
                raise RuntimeError(f"Expected league payload to be a dict for {uuid!r}")

        league_entry = self.build_league_entry(league_payload)
        self.dump_raw_json("league-list-store-raw.json", uuid, league_payload)
        self.set_store_item(uuid, league_entry)


LEAGUE_LIST_STORE = LeagueListStore()

