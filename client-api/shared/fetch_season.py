from __future__ import annotations

from periodic_updater import PeriodicUpdater
from sams_api_client import fetch_endpoint_direct


STORE_TTL_SECONDS = 24 * 60 * 60


class Season(PeriodicUpdater):
    def __init__(self) -> None:
        super().__init__(
            logger_name="competition-api.season",
            thread_name="season-updater",
            store_file_name="season-store.json",
            ttl_seconds=STORE_TTL_SECONDS,
        )

    def update_store(self, uuid: str | None = None) -> None:
        if uuid is None:
            payload = fetch_endpoint_direct("/seasons")

            if isinstance(payload, dict):
                seasons = payload.get("content", [])
            else:
                seasons = payload

            if not isinstance(seasons, list):
                raise RuntimeError("Expected /seasons to return a list payload")

            for season in seasons:
                if not isinstance(season, dict):
                    continue

                season_uuid = season.get("uuid")
                if not isinstance(season_uuid, str):
                    continue

                self.dump_raw_json("season-store-raw.json", season_uuid, season)
                self.set_store_item(season_uuid, self._normalize_season(season))
            return

        payload = fetch_endpoint_direct(f"/seasons/{uuid}")
        if not isinstance(payload, dict):
            raise RuntimeError(f"Expected season payload to be a dict for {uuid!r}")

        self.dump_raw_json("season-store-raw.json", uuid, payload)
        self.set_store_item(uuid, self._normalize_season(payload))

    def get(self, season_uuid: str) -> dict:
        self.wait_for_uuid(season_uuid)

        season = self.get_store_item(season_uuid)
        if season is not None:
            return season

        payload = fetch_endpoint_direct(f"/seasons/{season_uuid}")
        if not isinstance(payload, dict):
            raise RuntimeError(f"Expected season payload to be a dict for {season_uuid!r}")

        payload = self._normalize_season(payload)
        self.set_store_item(season_uuid, payload)

        return payload

    def _normalize_season(self, season: dict) -> dict:
        return {
            "uuid": season.get("uuid"),
            "name": season.get("name"),
            "startDate": season.get("startDate"),
            "endDate": season.get("endDate"),
            "currentSeason": season.get("currentSeason"),
        }


SEASON = Season()
