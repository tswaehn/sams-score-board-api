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
        )

    def update_store(self, uuid: str | None = None) -> None:
        if uuid is None:
            return

        payload = fetch_endpoint_direct(f"/associations/{uuid}")
        if not isinstance(payload, dict):
            raise RuntimeError(f"Expected association payload to be a dict for {uuid!r}")

        self.dump_raw_json("association-store-raw.json", uuid, payload)
        self.set_store_item(uuid, self._normalize_association(payload))

    def get(self, association_uuid: str) -> dict:
        self.wait_for_uuid(association_uuid)

        association = self.get_store_item(association_uuid)
        if association is not None:
            return association

        payload = fetch_endpoint_direct(f"/associations/{association_uuid}")
        if not isinstance(payload, dict):
            raise RuntimeError(f"Expected association payload to be a dict for {association_uuid!r}")

        payload = self._normalize_association(payload)
        self.set_store_item(association_uuid, payload)

        return payload

    def _normalize_association(self, association: dict) -> dict:
        return {
            "uuid": association.get("uuid"),
            "name": association.get("name"),
            "shortname": association.get("shortname"),
            "level": association.get("level"),
            "parentUuid": association.get("parentUuid"),
        }


ASSOCIATION = Association()
