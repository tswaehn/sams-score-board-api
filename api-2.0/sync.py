"""SAMS mirror synchronizer.

The synchronizer refreshes all seasons first. It then imports competitions by season,
followed by leagues by season. Associations and teams remain database-first
dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import threading
import time
from typing import Any
from urllib.parse import quote_plus, urlparse
from uuid import UUID

from database import Database
from models import Association, Competition, CompetitionMatch, CompetitionMatchGroupRanking, League, LeagueMatch, LeagueMatchDay, LeagueRanking, MatchGroup, Season, Team
from upstream_queue import UpstreamQueue


LOGGER = logging.getLogger("api2.sync")
UPSTREAM_PAGE_SIZE = 100
WRITE_BATCH_SIZE = 5


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


def _latest_upstream_update(payload: dict[str, Any]) -> str | None:
    candidates = [
        value
        for value in (payload.get("latestResultUpdate"), payload.get("latestStructuralUpdate"))
        if isinstance(value, str) and value.strip()
    ]
    if not candidates:
        return None

    def timestamp(value: str) -> float:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.timestamp()
        except ValueError:
            return float("-inf")

    return max(candidates, key=lambda value: (timestamp(value), value))


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

    def sync_once(self, *, force: bool = False) -> None:
        # Entities frequently share teams and associations.  Dedupe them per run
        # without weakening a later scheduled refresh.
        self._synced_association_uuids = set()
        self._synced_team_uuids = set()
        # Seasons are few and quick to write, so one short transaction is enough.
        with self.database.transaction():
            seasons = self._sync_seasons()
        for season in seasons:
            self._sync_entities_for_season("competition", season, force=force)
        for season in seasons:
            self._sync_entities_for_season("league", season, force=force)

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
        first = self.upstream.fetch(
            f"{endpoint}{separator}page=0&size={UPSTREAM_PAGE_SIZE}",
            priority=priority,
        )
        result = _items(first)
        total_pages = first.get("totalPages", 1) if isinstance(first, dict) else 1
        if not isinstance(total_pages, int):
            total_pages = 1
        for page in range(1, total_pages):
            result.extend(
                _items(
                    self.upstream.fetch(
                        f"{endpoint}{separator}page={page}&size={UPSTREAM_PAGE_SIZE}",
                        priority=priority,
                    )
                )
            )
        return result

    def _sync_seasons(self) -> list[Season]:
        seasons: list[Season] = []
        for payload in self._fetch_collection("seasons", priority=0):
            uuid = payload.get("uuid")
            if not isinstance(uuid, str):
                continue
            season = Season(
                uuid,
                payload.get("name"),
                payload.get("startDate"),
                payload.get("endDate"),
                bool(payload.get("currentSeason")),
                payload,
            )
            self.database.upsert_season(season)
            seasons.append(season)
        # ISO-8601 dates sort lexicographically.  End date and UUID make ordering
        # deterministic for incomplete or equal season records.
        return sorted(
            seasons,
            key=lambda season: (
                season.start_date or "",
                season.end_date or "",
                season.uuid,
            ),
            reverse=True,
        )

    def _sync_entities_for_season(self, entity: str, season: Season, *, force: bool = False) -> None:
        endpoint = f"{entity}s?season={quote_plus(season.uuid)}"
        summaries = self._fetch_collection(endpoint, priority=10)
        total = len(summaries)
        imported = 0
        skipped = 0
        LOGGER.info(
            "Syncing %s for season=%s name=%r total=%s force=%s",
            entity,
            season.uuid,
            season.name,
            total,
            force,
        )
        for batch_start in range(0, total, WRITE_BATCH_SIZE):
            batch = summaries[batch_start:batch_start + WRITE_BATCH_SIZE]
            # A failed batch rolls back at most 25 entities. This intentionally
            # bounds SQLite write-lock time during long upstream syncs.
            with self.database.transaction():
                for summary in batch:
                    uuid = summary.get("uuid")
                    if not isinstance(uuid, str):
                        skipped += 1
                        continue
                    already_synced = self.database.get_entity(entity, uuid) is not None
                    if already_synced and not force:
                        skipped += 1
                        continue
                    detail = self.upstream.fetch(f"{entity}s/{uuid}", priority=10)
                    payload = detail if isinstance(detail, dict) else summary
                    self._store_entity(entity, payload, season)
                    self._sync_entity_association(payload)
                    self._sync_entity_teams(entity, uuid, already_synced=already_synced)
                    if entity == "competition":
                        self._sync_competition_match_data(uuid)
                    elif entity == "league":
                        self._sync_league_match_data(uuid)
                    imported += 1
            position = min(batch_start + len(batch), total)
            if position % WRITE_BATCH_SIZE == 0 or position == total:
                LOGGER.info(
                    "Sync progress entity=%s season=%s processed=%s/%s imported=%s skipped=%s",
                    entity,
                    season.uuid,
                    position,
                    total,
                    imported,
                    skipped,
                )
        LOGGER.info(
            "Sync complete entity=%s season=%s total=%s imported=%s skipped=%s",
            entity,
            season.uuid,
            total,
            imported,
            skipped,
        )

    def _store_entity(self, entity: str, payload: dict[str, Any], requested_season: Season) -> None:
        uuid = payload.get("uuid")
        if not isinstance(uuid, str):
            return
        season_uuid = payload.get("seasonUuid") or _linked_uuid(payload, "season") or requested_season.uuid
        if not isinstance(season_uuid, str):
            raise RuntimeError(f"Entity {uuid} does not contain a season UUID")
        season = self._get_or_sync_season(season_uuid)
        association_uuid = payload.get("associationUuid") or _linked_uuid(payload, "association")
        # This is intentionally an enriched local payload. The upstream object is
        # preserved except for the locally propagated season state.
        enriched_payload = {**payload, "currentSeason": season.current}
        latest_upstream_update = _latest_upstream_update(payload)
        if entity == "competition":
            self.database.upsert_competition(Competition(uuid, season.uuid, season.current, latest_upstream_update, association_uuid, payload.get("name"), payload.get("gender"), enriched_payload))
        else:
            self.database.upsert_league(League(uuid, season.uuid, season.current, latest_upstream_update, association_uuid, payload.get("name"), payload.get("shortName"), payload.get("gender"), enriched_payload))

    def _get_or_sync_season(self, uuid: str) -> Season:
        payload = self.database.get_payload("seasons", uuid)
        if payload is None:
            fetched = self.upstream.fetch(f"seasons/{uuid}", priority=20)
            if not isinstance(fetched, dict):
                raise RuntimeError(f"Expected a season object for {uuid}")
            payload = fetched
            self.database.upsert_season(
                Season(uuid, payload.get("name"), payload.get("startDate"), payload.get("endDate"), bool(payload.get("currentSeason")), payload)
            )
        return Season(uuid, payload.get("name"), payload.get("startDate"), payload.get("endDate"), bool(payload.get("currentSeason")), payload)

    def _sync_entity_association(self, payload: dict[str, Any]) -> None:
        uuid = payload.get("associationUuid") or _linked_uuid(payload, "association")
        if isinstance(uuid, str):
            self._sync_association(uuid)

    def _sync_association(self, uuid: str) -> None:
        if uuid in self._synced_association_uuids:
            return
        if self.database.get_payload("associations", uuid) is not None:
            self._synced_association_uuids.add(uuid)
            return
        payload = self.upstream.fetch(f"associations/{uuid}", priority=20)
        if not isinstance(payload, dict):
            return
        self.database.upsert_association(Association(uuid, payload.get("name"), payload.get("shortname"), payload.get("level"), payload.get("parentUuid"), payload))
        self._synced_association_uuids.add(uuid)

    def _sync_entity_teams(self, entity: str, entity_uuid: str, *, already_synced: bool) -> None:
        if already_synced:
            # The relationship itself is persisted.  Reusing it avoids both the
            # remote team-list request and per-team detail requests on later runs.
            team_uuids = self.database.get_entity_team_uuids(entity, entity_uuid)
        else:
            teams = self._fetch_collection(f"{entity}s/{entity_uuid}/teams", priority=20)
            team_uuids = []
            for summary in teams:
                uuid = summary.get("uuid")
                if not isinstance(uuid, str):
                    continue
                team_uuids.append(uuid)

        for uuid in team_uuids:
            if uuid not in self._synced_team_uuids:
                cached_team = self.database.get_payload("teams", uuid)
                if cached_team is not None:
                    association_uuid = cached_team.get("associationUuid") or _linked_uuid(cached_team, "association")
                    if isinstance(association_uuid, str):
                        self._sync_association(association_uuid)
                    self._synced_team_uuids.add(uuid)
                    continue
                detail = self.upstream.fetch(f"teams/{uuid}", priority=20)
                if not isinstance(detail, dict):
                    raise RuntimeError(f"Expected a team object for {uuid}")
                payload = detail
                team = Team(uuid, payload.get("name"), payload.get("shortName") or payload.get("shortname"), payload.get("associationUuid") or _linked_uuid(payload, "association"), payload)
                self.database.upsert_team(team)
                if team.association_uuid:
                    self._sync_association(team.association_uuid)
                self._synced_team_uuids.add(uuid)
        if not already_synced:
            self.database.replace_entity_teams(entity, entity_uuid, team_uuids)

    def _sync_competition_match_data(self, competition_uuid: str) -> None:
        match_groups = self._fetch_collection(
            f"competitions/{competition_uuid}/match-groups", priority=20
        )
        LOGGER.info(
            "Syncing match data competition=%s matchGroups=%s",
            competition_uuid,
            len(match_groups),
        )
        for group_payload in match_groups:
            group_uuid = group_payload.get("uuid")
            if not isinstance(group_uuid, str):
                continue
            self.database.upsert_match_group(
                MatchGroup(
                    group_uuid,
                    competition_uuid,
                    group_payload.get("seasonUuid") if isinstance(group_payload.get("seasonUuid"), str) else None,
                    group_payload.get("name"),
                    group_payload.get("tourneyLevel") if isinstance(group_payload.get("tourneyLevel"), int) else None,
                    group_payload,
                )
            )
            matches = self._fetch_collection(
                f"match-groups/{group_uuid}/competition-matches", priority=20
            )
            for match_payload in matches:
                match_uuid = match_payload.get("uuid")
                if not isinstance(match_uuid, str):
                    continue
                self.database.upsert_competition_match(
                    CompetitionMatch(
                        match_uuid,
                        competition_uuid,
                        match_payload.get("matchGroupUuid") if isinstance(match_payload.get("matchGroupUuid"), str) else group_uuid,
                        match_payload.get("seasonUuid") if isinstance(match_payload.get("seasonUuid"), str) else None,
                        match_payload.get("date") if isinstance(match_payload.get("date"), str) else None,
                        match_payload.get("verified") if isinstance(match_payload.get("verified"), bool) else None,
                        match_payload,
                    )
                )
                result = match_payload.get("results")
                self.database.upsert_competition_match_result(
                    match_uuid,
                    competition_uuid,
                    result if isinstance(result, dict) else None,
                )
        try:
            rankings = self._fetch_collection(
                f"competitions/{competition_uuid}/rankings", priority=20
            )
            for ranking_payload in rankings:
                ranking_uuid = ranking_payload.get("uuid")
                if not isinstance(ranking_uuid, str):
                    continue
                self.database.upsert_competition_match_group_ranking(
                    CompetitionMatchGroupRanking(
                        ranking_uuid,
                        competition_uuid,
                        ranking_payload.get("matchGroupName") if isinstance(ranking_payload.get("matchGroupName"), str) else None,
                        ranking_payload,
                    )
                )
        except RuntimeError as exc:
            print(
                "ERROR: competition ranking sync failed after upstream retries "
                f"competition={competition_uuid}: {exc}",
                flush=True,
            )

    def _sync_league_match_data(self, league_uuid: str) -> None:
        match_days = self._fetch_collection(
            f"leagues/{league_uuid}/match-days", priority=20
        )
        LOGGER.info(
            "Syncing league match data league=%s matchDays=%s",
            league_uuid,
            len(match_days),
        )
        for day_payload in match_days:
            day_uuid = day_payload.get("uuid")
            if not isinstance(day_uuid, str):
                continue
            self.database.upsert_league_match_day(
                LeagueMatchDay(
                    day_uuid,
                    league_uuid,
                    day_payload.get("seasonUuid") if isinstance(day_payload.get("seasonUuid"), str) else None,
                    day_payload.get("name"),
                    day_payload.get("matchdate") if isinstance(day_payload.get("matchdate"), str) else None,
                    day_payload,
                )
            )
            matches = self._fetch_collection(
                f"match-days/{day_uuid}/league-matches", priority=20
            )
            for match_payload in matches:
                match_uuid = match_payload.get("uuid")
                if not isinstance(match_uuid, str):
                    continue
                self.database.upsert_league_match(
                    LeagueMatch(
                        match_uuid,
                        league_uuid,
                        match_payload.get("matchDayUuid") if isinstance(match_payload.get("matchDayUuid"), str) else day_uuid,
                        match_payload.get("seasonUuid") if isinstance(match_payload.get("seasonUuid"), str) else None,
                        match_payload.get("date") if isinstance(match_payload.get("date"), str) else None,
                        match_payload.get("verified") if isinstance(match_payload.get("verified"), bool) else None,
                        match_payload,
                    )
                )
                result = match_payload.get("results")
                self.database.upsert_league_match_result(
                    match_uuid,
                    league_uuid,
                    result if isinstance(result, dict) else None,
                )
        rankings = self._fetch_collection(f"leagues/{league_uuid}/rankings", priority=20)
        for ranking_payload in rankings:
            ranking_uuid = ranking_payload.get("uuid")
            if not isinstance(ranking_uuid, str):
                continue
            self.database.upsert_league_ranking(
                LeagueRanking(
                    ranking_uuid,
                    league_uuid,
                    ranking_payload.get("rank") if isinstance(ranking_payload.get("rank"), int) else None,
                    ranking_payload.get("teamName") if isinstance(ranking_payload.get("teamName"), str) else None,
                    ranking_payload,
                )
            )
