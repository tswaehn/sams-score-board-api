"""Historical mirror synchronizer.

The sequence is intentional: seasons are durable first; only non-current season
children are then scheduled.  This keeps the current season available for a future
live/short-TTL stage without repeatedly re-importing it here.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any
from urllib.parse import quote_plus, urlparse
from uuid import UUID

from database import Database
from models import Association, Competition, League, Season, Team
from upstream_queue import UpstreamQueue


LOGGER = logging.getLogger("api2.sync")


def _items(payload: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
    values = payload.get("content", []) if isinstance(payload, dict) else payload
    return [item for item in values if isinstance(item, dict)] if isinstance(values, list) else []


def _uuid_from_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    for part in urlparse(value).path.split("/"):
        try:
            return str(UUID(part))
        except ValueError:
            pass
    return None


def _linked_uuid(payload: dict[str, Any], name: str) -> str | None:
    links = payload.get("_links")
    link = links.get(name) if isinstance(links, dict) else None
    return _uuid_from_url(link.get("href")) if isinstance(link, dict) else None


class HistoricalSync:
    def __init__(self, database: Database, upstream: UpstreamQueue, *, repeat_after_seconds: int = 24 * 60 * 60) -> None:
        self.database = database
        self.upstream = upstream
        self.repeat_after_seconds = repeat_after_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_error: str | None = None
        self._last_completed_at: float | None = None
        self._synced_association_uuids: set[str] = set()
        self._synced_team_uuids: set[str] = set()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="historical-sync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def status(self) -> dict[str, Any]:
        return {"running": bool(self._thread and self._thread.is_alive()), "lastError": self._last_error,
                "lastCompletedAt": self._last_completed_at, "queuedRequests": self.upstream.pending_count}

    def sync_once(self) -> None:
        # Entities frequently share teams and associations.  Dedupe them per run
        # without weakening a later scheduled refresh.
        self._synced_association_uuids = set()
        self._synced_team_uuids = set()
        seasons = self._sync_seasons()
        for season in seasons:
            if season.current:
                continue
            self._sync_season_entities("competition", season.uuid)
            self._sync_season_entities("league", season.uuid)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.sync_once()
                self._last_error = None
                self._last_completed_at = time.time()
            except Exception as exc:
                self._last_error = str(exc)
                LOGGER.exception("Historical sync failed")
            self._stop.wait(self.repeat_after_seconds)

    def _fetch_collection(self, endpoint: str, *, priority: int) -> list[dict[str, Any]]:
        # SAMS uses Spring pagination.  Every page still travels through the one queue.
        separator = "&" if "?" in endpoint else "?"
        first = self.upstream.fetch(f"{endpoint}{separator}page=0&size=9999", priority=priority)
        result = _items(first)
        total_pages = first.get("totalPages", 1) if isinstance(first, dict) else 1
        if not isinstance(total_pages, int):
            total_pages = 1
        for page in range(1, total_pages):
            result.extend(_items(self.upstream.fetch(f"{endpoint}{separator}page={page}&size=9999", priority=priority)))
        return result

    def _sync_seasons(self) -> list[Season]:
        seasons: list[Season] = []
        for payload in self._fetch_collection("seasons", priority=0):
            uuid = payload.get("uuid")
            if not isinstance(uuid, str):
                continue
            season = Season(uuid, payload.get("name"), payload.get("startDate"), payload.get("endDate"), bool(payload.get("currentSeason")), payload)
            self.database.upsert_season(season)
            seasons.append(season)
        return seasons

    def _sync_season_entities(self, entity: str, season_uuid: str) -> None:
        endpoint = f"{entity}s?season={quote_plus(season_uuid)}"
        for summary in self._fetch_collection(endpoint, priority=10):
            uuid = summary.get("uuid")
            if not isinstance(uuid, str):
                continue
            detail = self.upstream.fetch(f"{entity}s/{uuid}", priority=10)
            payload = detail if isinstance(detail, dict) else summary
            self._store_entity(entity, payload, season_uuid)
            self._sync_entity_association(payload)
            self._sync_entity_teams(entity, uuid)

    def _store_entity(self, entity: str, payload: dict[str, Any], fallback_season_uuid: str) -> None:
        uuid = payload.get("uuid")
        if not isinstance(uuid, str):
            return
        season_uuid = payload.get("seasonUuid") or _linked_uuid(payload, "season") or fallback_season_uuid
        association_uuid = payload.get("associationUuid") or _linked_uuid(payload, "association")
        if entity == "competition":
            self.database.upsert_competition(Competition(uuid, season_uuid, association_uuid, payload.get("name"), payload.get("gender"), payload))
        else:
            self.database.upsert_league(League(uuid, season_uuid, association_uuid, payload.get("name"), payload.get("shortName"), payload.get("gender"), payload))

    def _sync_entity_association(self, payload: dict[str, Any]) -> None:
        uuid = payload.get("associationUuid") or _linked_uuid(payload, "association")
        if isinstance(uuid, str):
            self._sync_association(uuid)

    def _sync_association(self, uuid: str) -> None:
        if uuid in self._synced_association_uuids:
            return
        payload = self.upstream.fetch(f"associations/{uuid}", priority=20)
        if not isinstance(payload, dict):
            return
        self.database.upsert_association(Association(uuid, payload.get("name"), payload.get("shortname"), payload.get("level"), payload.get("parentUuid"), payload))
        self._synced_association_uuids.add(uuid)

    def _sync_entity_teams(self, entity: str, entity_uuid: str) -> None:
        teams = self._fetch_collection(f"{entity}s/{entity_uuid}/teams", priority=20)
        team_uuids: list[str] = []
        for summary in teams:
            uuid = summary.get("uuid")
            if not isinstance(uuid, str):
                continue
            if uuid not in self._synced_team_uuids:
                detail = self.upstream.fetch(f"teams/{uuid}", priority=20)
                payload = detail if isinstance(detail, dict) else summary
                team = Team(uuid, payload.get("name"), payload.get("shortName") or payload.get("shortname"), payload.get("associationUuid") or _linked_uuid(payload, "association"), payload)
                self.database.upsert_team(team)
                if team.association_uuid:
                    self._sync_association(team.association_uuid)
                self._synced_team_uuids.add(uuid)
            team_uuids.append(uuid)
        self.database.replace_entity_teams(entity, entity_uuid, team_uuids)
