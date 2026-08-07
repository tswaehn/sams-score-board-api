"""Database-facing models for the API 2.0 historical mirror."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Season:
    uuid: str
    name: str | None
    start_date: str | None
    end_date: str | None
    current: bool
    payload: dict[str, Any]


@dataclass(frozen=True)
class Association:
    uuid: str
    name: str | None
    shortname: str | None
    level: str | None
    parent_uuid: str | None
    payload: dict[str, Any]


@dataclass(frozen=True)
class Team:
    uuid: str
    name: str | None
    shortname: str | None
    association_uuid: str | None
    payload: dict[str, Any]


@dataclass(frozen=True)
class Competition:
    uuid: str
    season_uuid: str
    is_current: bool
    latest_upstream_update: str | None
    association_uuid: str | None
    name: str | None
    gender: str | None
    payload: dict[str, Any]


@dataclass(frozen=True)
class League:
    uuid: str
    season_uuid: str
    is_current: bool
    latest_upstream_update: str | None
    association_uuid: str | None
    name: str | None
    shortname: str | None
    gender: str | None
    payload: dict[str, Any]


@dataclass(frozen=True)
class MatchGroup:
    uuid: str
    competition_uuid: str
    season_uuid: str | None
    name: str | None
    tourney_level: int | None
    payload: dict[str, Any]


@dataclass(frozen=True)
class CompetitionMatch:
    uuid: str
    competition_uuid: str
    match_group_uuid: str | None
    season_uuid: str | None
    match_date: str | None
    verified: bool | None
    payload: dict[str, Any]


@dataclass(frozen=True)
class CompetitionMatchGroupRanking:
    uuid: str
    competition_uuid: str
    match_group_name: str | None
    payload: dict[str, Any]


@dataclass(frozen=True)
class LeagueMatchDay:
    uuid: str
    league_uuid: str
    season_uuid: str | None
    name: str | None
    match_date: str | None
    payload: dict[str, Any]


@dataclass(frozen=True)
class LeagueMatch:
    uuid: str
    league_uuid: str
    match_day_uuid: str | None
    season_uuid: str | None
    match_date: str | None
    verified: bool | None
    payload: dict[str, Any]


@dataclass(frozen=True)
class LeagueRanking:
    uuid: str
    league_uuid: str
    rank: int | None
    team_name: str | None
    payload: dict[str, Any]
