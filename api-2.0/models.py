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
    association_uuid: str | None
    name: str | None
    gender: str | None
    payload: dict[str, Any]


@dataclass(frozen=True)
class League:
    uuid: str
    season_uuid: str
    is_current: bool
    association_uuid: str | None
    name: str | None
    shortname: str | None
    gender: str | None
    payload: dict[str, Any]
