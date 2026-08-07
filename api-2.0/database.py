"""SQLite persistence and read models.  All writes happen in the sync stage."""

from __future__ import annotations

from contextlib import contextmanager
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable

from models import Association, Competition, CompetitionMatch, CompetitionMatchGroupRanking, League, LeagueMatch, LeagueMatchDay, LeagueRanking, MatchGroup, Season, Team


class Database:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()

    def connection(self) -> sqlite3.Connection:
        connection = getattr(self._local, "connection", None)
        if connection is None:
            connection = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
            connection.execute("PRAGMA temp_store = MEMORY")
            # Keep approximately 64 MiB of pages in SQLite's in-process cache.
            connection.execute("PRAGMA cache_size = -65536")
            connection.execute("PRAGMA busy_timeout = 30000")
            self._local.connection = connection
        return connection

    @contextmanager
    def transaction(self):
        """Batch writes without changing standalone repository method semantics."""
        connection = self.connection()
        depth = getattr(self._local, "transaction_depth", 0)
        if depth == 0:
            connection.execute("BEGIN IMMEDIATE")
        self._local.transaction_depth = depth + 1
        try:
            yield
        except Exception:
            self._local.transaction_depth = depth
            if depth == 0:
                connection.rollback()
            raise
        else:
            self._local.transaction_depth = depth
            if depth == 0:
                connection.commit()

    def _commit_if_needed(self) -> None:
        if getattr(self._local, "transaction_depth", 0) == 0:
            self.connection().commit()

    def initialize(self) -> None:
        self.connection().executescript(
            """
            CREATE TABLE IF NOT EXISTS seasons (
              uuid TEXT PRIMARY KEY, name TEXT, start_date TEXT, end_date TEXT,
              is_current INTEGER NOT NULL, payload_json TEXT NOT NULL, synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS associations (
              uuid TEXT PRIMARY KEY, name TEXT, shortname TEXT, level TEXT, parent_uuid TEXT,
              payload_json TEXT NOT NULL, synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS teams (
              uuid TEXT PRIMARY KEY, name TEXT, shortname TEXT, association_uuid TEXT,
              payload_json TEXT NOT NULL, synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS competitions (
              uuid TEXT PRIMARY KEY, season_uuid TEXT NOT NULL REFERENCES seasons(uuid), association_uuid TEXT,
              is_current INTEGER NOT NULL DEFAULT 0, latest_upstream_update TEXT, name TEXT, gender TEXT, payload_json TEXT NOT NULL, synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS leagues (
              uuid TEXT PRIMARY KEY, season_uuid TEXT NOT NULL REFERENCES seasons(uuid), association_uuid TEXT,
              is_current INTEGER NOT NULL DEFAULT 0, latest_upstream_update TEXT, name TEXT, shortname TEXT, gender TEXT, payload_json TEXT NOT NULL, synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS competition_teams (
              competition_uuid TEXT NOT NULL REFERENCES competitions(uuid) ON DELETE CASCADE,
              team_uuid TEXT NOT NULL REFERENCES teams(uuid), PRIMARY KEY (competition_uuid, team_uuid)
            );
            CREATE TABLE IF NOT EXISTS league_teams (
              league_uuid TEXT NOT NULL REFERENCES leagues(uuid) ON DELETE CASCADE,
              team_uuid TEXT NOT NULL REFERENCES teams(uuid), PRIMARY KEY (league_uuid, team_uuid)
            );
            CREATE TABLE IF NOT EXISTS match_groups (
              uuid TEXT PRIMARY KEY, competition_uuid TEXT NOT NULL REFERENCES competitions(uuid) ON DELETE CASCADE,
              season_uuid TEXT, name TEXT, tourney_level INTEGER, payload_json TEXT NOT NULL,
              synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS competition_matches (
              uuid TEXT PRIMARY KEY, competition_uuid TEXT NOT NULL REFERENCES competitions(uuid) ON DELETE CASCADE,
              match_group_uuid TEXT REFERENCES match_groups(uuid) ON DELETE SET NULL, season_uuid TEXT,
              match_date TEXT, verified INTEGER, payload_json TEXT NOT NULL, synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS competition_match_results (
              match_uuid TEXT PRIMARY KEY REFERENCES competition_matches(uuid) ON DELETE CASCADE,
              competition_uuid TEXT NOT NULL REFERENCES competitions(uuid) ON DELETE CASCADE,
              payload_json TEXT NOT NULL, synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS competition_match_group_rankings (
              uuid TEXT PRIMARY KEY, competition_uuid TEXT NOT NULL REFERENCES competitions(uuid) ON DELETE CASCADE,
              match_group_name TEXT, payload_json TEXT NOT NULL, synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS league_match_days (
              uuid TEXT PRIMARY KEY, league_uuid TEXT NOT NULL REFERENCES leagues(uuid) ON DELETE CASCADE,
              season_uuid TEXT, name TEXT, match_date TEXT, payload_json TEXT NOT NULL,
              synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS league_matches (
              uuid TEXT PRIMARY KEY, league_uuid TEXT NOT NULL REFERENCES leagues(uuid) ON DELETE CASCADE,
              match_day_uuid TEXT REFERENCES league_match_days(uuid) ON DELETE SET NULL, season_uuid TEXT,
              match_date TEXT, verified INTEGER, payload_json TEXT NOT NULL, synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS league_match_results (
              match_uuid TEXT PRIMARY KEY REFERENCES league_matches(uuid) ON DELETE CASCADE,
              league_uuid TEXT NOT NULL REFERENCES leagues(uuid) ON DELETE CASCADE,
              payload_json TEXT NOT NULL, synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS league_rankings (
              uuid TEXT PRIMARY KEY, league_uuid TEXT NOT NULL REFERENCES leagues(uuid) ON DELETE CASCADE,
              rank INTEGER, team_name TEXT, payload_json TEXT NOT NULL, synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS competitions_season_idx ON competitions(season_uuid);
            CREATE INDEX IF NOT EXISTS leagues_season_idx ON leagues(season_uuid);
            CREATE INDEX IF NOT EXISTS match_groups_competition_idx ON match_groups(competition_uuid);
            CREATE INDEX IF NOT EXISTS competition_matches_competition_idx ON competition_matches(competition_uuid);
            CREATE INDEX IF NOT EXISTS competition_rankings_competition_idx ON competition_match_group_rankings(competition_uuid);
            CREATE INDEX IF NOT EXISTS league_match_days_league_idx ON league_match_days(league_uuid);
            CREATE INDEX IF NOT EXISTS league_matches_league_idx ON league_matches(league_uuid);
            CREATE INDEX IF NOT EXISTS league_rankings_league_idx ON league_rankings(league_uuid);
            """
        )
        # Existing API 2.0 databases are migrated in place.
        self._ensure_column("competitions", "is_current", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column("leagues", "is_current", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column("competitions", "latest_upstream_update", "TEXT")
        self._ensure_column("leagues", "latest_upstream_update", "TEXT")
        self.connection().commit()

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        columns = {row["name"] for row in self.connection().execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            self.connection().execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    @staticmethod
    def _payload(payload: dict[str, Any]) -> str:
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    def upsert_season(self, item: Season) -> None:
        self.connection().execute("""INSERT INTO seasons VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
          ON CONFLICT(uuid) DO UPDATE SET name=excluded.name,start_date=excluded.start_date,end_date=excluded.end_date,
          is_current=excluded.is_current,payload_json=excluded.payload_json,synced_at=CURRENT_TIMESTAMP""",
          (item.uuid, item.name, item.start_date, item.end_date, int(item.current), self._payload(item.payload)))
        self._commit_if_needed()

    def upsert_association(self, item: Association) -> None:
        self.connection().execute("""INSERT INTO associations VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
          ON CONFLICT(uuid) DO UPDATE SET name=excluded.name,shortname=excluded.shortname,level=excluded.level,
          parent_uuid=excluded.parent_uuid,payload_json=excluded.payload_json,synced_at=CURRENT_TIMESTAMP""",
          (item.uuid, item.name, item.shortname, item.level, item.parent_uuid, self._payload(item.payload)))
        self._commit_if_needed()

    def upsert_team(self, item: Team) -> None:
        self.connection().execute("""INSERT INTO teams VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
          ON CONFLICT(uuid) DO UPDATE SET name=excluded.name,shortname=excluded.shortname,association_uuid=excluded.association_uuid,
          payload_json=excluded.payload_json,synced_at=CURRENT_TIMESTAMP""",
          (item.uuid, item.name, item.shortname, item.association_uuid, self._payload(item.payload)))
        self._commit_if_needed()

    def upsert_competition(self, item: Competition) -> None:
        self.connection().execute("""INSERT INTO competitions
          (uuid, season_uuid, association_uuid, is_current, latest_upstream_update, name, gender, payload_json, synced_at)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
          ON CONFLICT(uuid) DO UPDATE SET season_uuid=excluded.season_uuid,association_uuid=excluded.association_uuid,is_current=excluded.is_current,
          latest_upstream_update=excluded.latest_upstream_update,name=excluded.name,gender=excluded.gender,payload_json=excluded.payload_json,synced_at=CURRENT_TIMESTAMP""",
          (item.uuid, item.season_uuid, item.association_uuid, int(item.is_current), item.latest_upstream_update, item.name, item.gender, self._payload(item.payload)))
        self._commit_if_needed()

    def upsert_league(self, item: League) -> None:
        self.connection().execute("""INSERT INTO leagues
          (uuid, season_uuid, association_uuid, is_current, latest_upstream_update, name, shortname, gender, payload_json, synced_at)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
          ON CONFLICT(uuid) DO UPDATE SET season_uuid=excluded.season_uuid,association_uuid=excluded.association_uuid,is_current=excluded.is_current,
          latest_upstream_update=excluded.latest_upstream_update,name=excluded.name,shortname=excluded.shortname,gender=excluded.gender,payload_json=excluded.payload_json,synced_at=CURRENT_TIMESTAMP""",
          (item.uuid, item.season_uuid, item.association_uuid, int(item.is_current), item.latest_upstream_update, item.name, item.shortname, item.gender, self._payload(item.payload)))
        self._commit_if_needed()

    def replace_entity_teams(self, entity: str, entity_uuid: str, team_uuids: Iterable[str]) -> None:
        table = "competition_teams" if entity == "competition" else "league_teams"
        column = f"{entity}_uuid"
        connection = self.connection()
        connection.execute(f"DELETE FROM {table} WHERE {column} = ?", (entity_uuid,))
        connection.executemany(f"INSERT OR IGNORE INTO {table} ({column}, team_uuid) VALUES (?, ?)", ((entity_uuid, uuid) for uuid in team_uuids))
        self._commit_if_needed()

    def get_entity_team_uuids(self, entity: str, entity_uuid: str) -> list[str]:
        table = "competition_teams" if entity == "competition" else "league_teams"
        column = f"{entity}_uuid"
        return [
            row["team_uuid"]
            for row in self.connection().execute(
                f"SELECT team_uuid FROM {table} WHERE {column} = ? ORDER BY team_uuid",
                (entity_uuid,),
            )
        ]

    def upsert_match_group(self, item: MatchGroup) -> None:
        self.connection().execute("""INSERT INTO match_groups
          (uuid, competition_uuid, season_uuid, name, tourney_level, payload_json, synced_at)
          VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
          ON CONFLICT(uuid) DO UPDATE SET competition_uuid=excluded.competition_uuid,season_uuid=excluded.season_uuid,
          name=excluded.name,tourney_level=excluded.tourney_level,payload_json=excluded.payload_json,synced_at=CURRENT_TIMESTAMP""",
          (item.uuid, item.competition_uuid, item.season_uuid, item.name, item.tourney_level, self._payload(item.payload)))
        self._commit_if_needed()

    def upsert_competition_match(self, item: CompetitionMatch) -> None:
        self.connection().execute("""INSERT INTO competition_matches
          (uuid, competition_uuid, match_group_uuid, season_uuid, match_date, verified, payload_json, synced_at)
          VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
          ON CONFLICT(uuid) DO UPDATE SET competition_uuid=excluded.competition_uuid,match_group_uuid=excluded.match_group_uuid,
          season_uuid=excluded.season_uuid,match_date=excluded.match_date,verified=excluded.verified,
          payload_json=excluded.payload_json,synced_at=CURRENT_TIMESTAMP""",
          (item.uuid, item.competition_uuid, item.match_group_uuid, item.season_uuid, item.match_date,
           None if item.verified is None else int(item.verified), self._payload(item.payload)))
        self._commit_if_needed()

    def upsert_competition_match_result(self, match_uuid: str, competition_uuid: str, payload: dict[str, Any] | None) -> None:
        connection = self.connection()
        if payload is None:
            connection.execute("DELETE FROM competition_match_results WHERE match_uuid = ?", (match_uuid,))
        else:
            connection.execute("""INSERT INTO competition_match_results
              (match_uuid, competition_uuid, payload_json, synced_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
              ON CONFLICT(match_uuid) DO UPDATE SET competition_uuid=excluded.competition_uuid,
              payload_json=excluded.payload_json,synced_at=CURRENT_TIMESTAMP""",
              (match_uuid, competition_uuid, self._payload(payload)))
        self._commit_if_needed()

    def upsert_competition_match_group_ranking(self, item: CompetitionMatchGroupRanking) -> None:
        self.connection().execute("""INSERT INTO competition_match_group_rankings
          (uuid, competition_uuid, match_group_name, payload_json, synced_at)
          VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
          ON CONFLICT(uuid) DO UPDATE SET competition_uuid=excluded.competition_uuid,
          match_group_name=excluded.match_group_name,payload_json=excluded.payload_json,synced_at=CURRENT_TIMESTAMP""",
          (item.uuid, item.competition_uuid, item.match_group_name, self._payload(item.payload)))
        self._commit_if_needed()

    def upsert_league_match_day(self, item: LeagueMatchDay) -> None:
        self.connection().execute("""INSERT INTO league_match_days
          (uuid, league_uuid, season_uuid, name, match_date, payload_json, synced_at)
          VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
          ON CONFLICT(uuid) DO UPDATE SET league_uuid=excluded.league_uuid,season_uuid=excluded.season_uuid,
          name=excluded.name,match_date=excluded.match_date,payload_json=excluded.payload_json,synced_at=CURRENT_TIMESTAMP""",
          (item.uuid, item.league_uuid, item.season_uuid, item.name, item.match_date, self._payload(item.payload)))
        self._commit_if_needed()

    def upsert_league_match(self, item: LeagueMatch) -> None:
        self.connection().execute("""INSERT INTO league_matches
          (uuid, league_uuid, match_day_uuid, season_uuid, match_date, verified, payload_json, synced_at)
          VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
          ON CONFLICT(uuid) DO UPDATE SET league_uuid=excluded.league_uuid,match_day_uuid=excluded.match_day_uuid,
          season_uuid=excluded.season_uuid,match_date=excluded.match_date,verified=excluded.verified,
          payload_json=excluded.payload_json,synced_at=CURRENT_TIMESTAMP""",
          (item.uuid, item.league_uuid, item.match_day_uuid, item.season_uuid, item.match_date,
           None if item.verified is None else int(item.verified), self._payload(item.payload)))
        self._commit_if_needed()

    def upsert_league_match_result(self, match_uuid: str, league_uuid: str, payload: dict[str, Any] | None) -> None:
        connection = self.connection()
        if payload is None:
            connection.execute("DELETE FROM league_match_results WHERE match_uuid = ?", (match_uuid,))
        else:
            connection.execute("""INSERT INTO league_match_results
              (match_uuid, league_uuid, payload_json, synced_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
              ON CONFLICT(match_uuid) DO UPDATE SET league_uuid=excluded.league_uuid,
              payload_json=excluded.payload_json,synced_at=CURRENT_TIMESTAMP""",
              (match_uuid, league_uuid, self._payload(payload)))
        self._commit_if_needed()

    def upsert_league_ranking(self, item: LeagueRanking) -> None:
        self.connection().execute("""INSERT INTO league_rankings
          (uuid, league_uuid, rank, team_name, payload_json, synced_at)
          VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
          ON CONFLICT(uuid) DO UPDATE SET league_uuid=excluded.league_uuid,rank=excluded.rank,
          team_name=excluded.team_name,payload_json=excluded.payload_json,synced_at=CURRENT_TIMESTAMP""",
          (item.uuid, item.league_uuid, item.rank, item.team_name, self._payload(item.payload)))
        self._commit_if_needed()

    def list_entities(self, entity: str, season_uuid: str | None = None) -> list[dict[str, Any]]:
        table = "competitions" if entity == "competition" else "leagues"
        query = f"SELECT payload_json FROM {table}"
        params: tuple[str, ...] = ()
        if season_uuid:
            query += " WHERE season_uuid = ?"
            params = (season_uuid,)
        query += " ORDER BY name COLLATE NOCASE"
        return [json.loads(row["payload_json"]) for row in self.connection().execute(query, params)]

    def get_entity(self, entity: str, uuid: str) -> dict[str, Any] | None:
        table = "competitions" if entity == "competition" else "leagues"
        row = self.connection().execute(f"SELECT payload_json FROM {table} WHERE uuid = ?", (uuid,)).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def get_payload(self, table: str, uuid: str) -> dict[str, Any] | None:
        """Return an already-synced raw/enriched payload without an upstream call."""
        if table not in {"seasons", "associations", "teams", "competitions", "leagues"}:
            raise ValueError(f"Unsupported table: {table}")
        row = self.connection().execute(
            f"SELECT payload_json FROM {table} WHERE uuid = ?", (uuid,)
        ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def list_seasons(self) -> list[dict[str, Any]]:
        return [json.loads(row["payload_json"]) for row in self.connection().execute("SELECT payload_json FROM seasons ORDER BY start_date DESC")]

    def status(self) -> dict[str, int]:
        return {table: self.connection().execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("seasons", "competitions", "leagues", "teams", "associations", "match_groups", "competition_matches", "competition_match_results", "competition_match_group_rankings", "league_match_days", "league_matches", "league_match_results", "league_rankings")}
