from __future__ import annotations

from periodic_updater import PeriodicUpdater
from sams_api_client import fetch_endpoint_direct


STORE_TTL_SECONDS = 24 * 60 * 60


class Association(PeriodicUpdater):
    def __init__(self) -> None:
        super().__init__(
            logger_name="competition-api.association",
            thread_name="association-updater",
            store_file_name="association-store.json",
            ttl_seconds=STORE_TTL_SECONDS,
            update_callback=self.updateAll,
        )

    def updateAll(self, current_season: bool | None = None) -> list[dict]:
        payload = fetch_endpoint_direct("/associations")

        if isinstance(payload, dict):
            associations = payload.get("content", [])
        else:
            associations = payload

        if not isinstance(associations, list):
            raise RuntimeError("Expected /associations to return a list payload")

        normalized_associations = []
        for association in associations:
            if not isinstance(association, dict):
                continue

            association_uuid = association.get("uuid")
            if not isinstance(association_uuid, str):
                continue

            normalized_associations.append(association)

        self.dump_raw_json("association-store-raw.json", payload)
        self.replace_store({
            association["uuid"]: association for association in normalized_associations
        })

        return normalized_associations

    def get(self, association_uuid: str, current_season: bool | None = None) -> dict:
        self.wait_until_store_loaded()

        association = self.get_store_item(association_uuid)
        if association is not None:
            return association

        payload = fetch_endpoint_direct(f"/associations/{association_uuid}")
        if not isinstance(payload, dict):
            raise RuntimeError(f"Expected association payload to be a dict for {association_uuid!r}")

        self.set_store_item(association_uuid, payload)

        return payload


ASSOCIATION = Association()
