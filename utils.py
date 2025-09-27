from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from html import escape
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError

from config import CONFIG

_NAV_HTML = (
    "<nav>"
    "<a href='/'>Home</a>"
    "<a href='/upcoming-games'>Upcoming Games</a>"
    "<a href='/live'>Live</a>"
    "<a href='/series'>Series</a>"
    "<a href='/teams'>Teams</a>"
    "<a href='/rankings'>Rankings</a>"
    "<a href='/health'>Health</a>"
    "</nav>"
)


def execute_get_request(url: Optional[str] = None) -> str:
    """Execute a HTTP GET request using ``url`` or the configured default."""
    target_url = url or CONFIG.default_url
    if not target_url:
        raise ValueError("No URL provided and no default configured.")

    try:
        with urllib.request.urlopen(target_url) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset)
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"GET request to {target_url!r} failed: {exc}") from exc


def download_json_to_file(file_path: str, json_payload: str) -> str:
    """Persist ``json_payload`` to ``file_path``."""
    try:
        with open(file_path, "w", encoding="utf-8") as output:
            output.write(json_payload)
        return file_path
    except OSError as exc:
        raise RuntimeError(f"Unable to write to {file_path!r}: {exc}") from exc


def get_series_uuid_to_name(url: Optional[str] = None) -> Dict[str, str]:
    """Fetch the JSON payload and return a mapping of series UUIDs to names."""
    payload = execute_get_request(url)
    return extract_series_mapping(payload)


def get_upcoming_games(limit: int = 10, url: Optional[str] = None) -> List[dict]:
    """Return the upcoming matches with key metadata."""
    payload = execute_get_request(url)
    return extract_upcoming_games(payload, limit=limit)


def extract_series_mapping(payload: str) -> Dict[str, str]:
    """Return a mapping of match-series UUIDs to their display names."""
    document = json.loads(payload)
    match_series = document.get("matchSeries") or {}

    return {
        series_uuid: series_info.get("name", "")
        for series_uuid, series_info in match_series.items()
        if isinstance(series_info, dict)
    }


def extract_series_list(payload: str) -> List[Dict[str, Any]]:
    """Return a list of match series with metadata suitable for rendering."""
    document = json.loads(payload)
    match_series = document.get("matchSeries") or {}

    series_list: List[Dict[str, Any]] = []
    for series_uuid, series_info in match_series.items():
        if not isinstance(series_info, dict):
            continue
        series_list.append(
            {
                "uuid": series_uuid,
                "name": series_info.get("name", ""),
                "shortName": series_info.get("shortName", ""),
                "class": series_info.get("class", ""),
                "gender": series_info.get("gender", ""),
                "orderLevel": series_info.get("orderLevel"),
            }
        )

    series_list.sort(key=lambda entry: (entry.get("orderLevel") is None, entry.get("orderLevel", 0)))
    return series_list


def extract_upcoming_games(payload: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Return the most recently scheduled future matches ordered by kickoff descending."""
    document = json.loads(payload)
    match_days = document.get("matchDays") or []
    match_states = document.get("matchStates") or {}

    upcoming: List[Dict[str, Any]] = []
    for day in match_days:
        day_iso = day.get("date")
        for match in day.get("matches", []):
            match_uuid = match.get("id")
            scheduled_ms = match.get("date")
            state = match_states.get(match_uuid, {}) if match_uuid else {}

            upcoming.append(
                {
                    "matchUuid": match_uuid,
                    "matchSeriesUuid": match.get("matchSeries"),
                    "scheduledEpochMs": scheduled_ms,
                    "scheduledIso": _epoch_ms_to_iso(scheduled_ms),
                    "dayIso": day_iso,
                    "team1": match.get("teamDescription1"),
                    "team2": match.get("teamDescription2"),
                    "finished": state.get("finished"),
                    "finalized": state.get("finalized"),
                }
            )

    upcoming.sort(key=lambda entry: entry.get("scheduledEpochMs") or 0, reverse=True)
    return upcoming[:limit]


def render_upcoming_games_html(payload: str, limit: int = 10) -> str:
    """Render a simple HTML page listing the upcoming games."""
    series_mapping = extract_series_mapping(payload)
    games = extract_upcoming_games(payload, limit=limit)

    items: List[str] = []
    for game in games:
        series_name = series_mapping.get(game.get("matchSeriesUuid"), "")
        scheduled = game.get("scheduledIso") or "Unknown time"
        team1 = escape(game.get("team1", "Unknown"))
        team2 = escape(game.get("team2", "Unknown"))
        status = _render_status(game)
        sets = game.get("sets") or []
        set_items = []
        for match_set in sets:
            number = match_set.get("number")
            team1_points = match_set.get("team1")
            team2_points = match_set.get("team2")
            set_items.append(
                f"<li>Set {number}: {team1_points}-{team2_points}</li>"
            )
        if set_items:
            sets_markup = (
                f"<div class='match-sets'>Sets played: {len(sets)}</div>"
                f"<ul class='set-list'>{''.join(set_items)}</ul>"
            )
        else:
            sets_markup = "<div class='match-sets'>Sets played: 0</div>"
        items.append(
            "<li>"
            f"<div class='match-series'>{escape(series_name)}</div>"
            f"<div class='match-teams'>{team1} vs {team2}</div>"
            f"<div class='match-time'>{escape(scheduled)}</div>"
            f"<div class='match-status'>{status}</div>"
            f"{sets_markup}"
            "</li>"
        )

    if not items:
        items.append("<li>No games found.</li>")

    list_markup = "\n".join(items)
    return (
        "<!DOCTYPE html>"
        "<html lang='en'>"
        "<head>"
        "<meta charset='utf-8'/>"
        "<title>Upcoming Games</title>"
        "<style>"
        "body{font-family:Arial,sans-serif;margin:2rem;background:#f5f5f5;}"
        "h1{margin-bottom:1rem;}"
        "ul{list-style:none;padding:0;}"
        "li{background:#fff;padding:1rem;margin-bottom:1rem;border-radius:8px;"
        "box-shadow:0 1px 3px rgba(0,0,0,0.1);}"
        ".match-series{font-weight:bold;color:#005a9c;margin-bottom:0.25rem;}"
        ".match-teams{font-size:1.1rem;margin-bottom:0.25rem;}"
        ".match-time{color:#555;margin-bottom:0.25rem;}"
        ".match-status{font-size:0.9rem;color:#777;}"
        ".match-sets{margin-top:0.5rem;color:#333;}"
        ".set-list{list-style:none;padding:0;margin:0.5rem 0 0;display:flex;flex-wrap:wrap;gap:0.5rem;}"
        ".set-list li{background:#e7effa;padding:0.25rem 0.5rem;border-radius:4px;}"
        "nav a{margin-right:1rem;}"
        "</style>"
        "</head>"
        "<body>"
        f"{_NAV_HTML}"
        "<h1>Upcoming Games</h1>"
        f"<ul>{list_markup}</ul>"
        "</body>"
        "</html>"
    )


def render_series_html(payload: str) -> str:
    """Render an HTML page listing all match series (leagues)."""
    series_list = extract_series_list(payload)
    items: List[str] = []
    for series in series_list:
        name = escape(series.get("name") or "Unknown series")
        short_name = escape(series.get("shortName") or "")
        league_class = escape(series.get("class") or "")
        gender = escape(series.get("gender") or "")
        raw_uuid = series.get("uuid") or ""
        uuid = escape(raw_uuid)
        ranking_link = escape(f"/rankings?series={raw_uuid}")
        details = " | ".join(filter(None, [short_name, league_class, gender]))
        meta = f"<div class='series-meta'>{details}</div>" if details else ""
        items.append(
            "<li>"
            f"<div class='series-name'><a class='series-link' href='{ranking_link}'>{name}</a></div>"
            f"{meta}"
            f"<div class='series-uuid'>UUID: {uuid}</div>"
            "</li>"
        )

    if not items:
        items.append("<li>No series available.</li>")

    list_markup = "\n".join(items)
    return (
        "<!DOCTYPE html>"
        "<html lang='en'>"
        "<head>"
        "<meta charset='utf-8'/>"
        "<title>Match Series</title>"
        "<style>"
        "body{font-family:Arial,sans-serif;margin:2rem;background:#f5f5f5;}"
        "h1{margin-bottom:1rem;}"
        "ul{list-style:none;padding:0;}"
        "li{background:#fff;padding:1rem;margin-bottom:1rem;border-radius:8px;"
        "box-shadow:0 1px 3px rgba(0,0,0,0.1);}"
        ".series-name{font-weight:bold;color:#005a9c;margin-bottom:0.25rem;}"
        ".series-meta{color:#555;margin-bottom:0.25rem;}"
        ".series-uuid{font-size:0.85rem;color:#777;}"
        ".series-link{color:#005a9c;text-decoration:none;}"
        ".series-link:hover{text-decoration:underline;}"
        "nav a{margin-right:1rem;}"
        "</style>"
        "</head>"
        "<body>"
        f"{_NAV_HTML}"
        "<h1>Match Series</h1>"
        f"<ul>{list_markup}</ul>"
        "</body>"
        "</html>"
    )


def render_teams_html(payload: str, selected_series_uuid: Optional[str] = None) -> str:
    """Render a page with a dropdown of series and a team table for the selection."""
    document = json.loads(payload)
    match_series = document.get("matchSeries") or {}
    series_list = extract_series_list(payload)

    if not series_list:
        selected_series_uuid = None
    elif selected_series_uuid not in match_series:
        selected_series_uuid = series_list[0]["uuid"]

    options_markup: List[str] = []
    for series in series_list:
        uuid = series.get("uuid", "")
        name = series.get("name") or "Unnamed series"
        selected_attr = " selected" if uuid == selected_series_uuid else ""
        options_markup.append(
            f"<option value='{escape(uuid)}'{selected_attr}>{escape(name)}</option>"
        )

    selected_series_info = (
        match_series.get(selected_series_uuid) if selected_series_uuid else None
    )
    teams = selected_series_info.get("teams", []) if isinstance(selected_series_info, dict) else []

    rows: List[str] = []
    for team in teams:
        name = escape(team.get("name", "Unnamed team"))
        short_name = escape(team.get("shortName", ""))
        letter = escape(team.get("letter", ""))
        team_id = escape(team.get("id", ""))
        logo = escape(team.get("logoImage200", ""))
        logo_markup = (
            f"<img src='{logo}' alt='{name} logo' class='team-logo'/>"
            if logo
            else ""
        )
        rows.append(
            "<tr>"
            f"<td>{name}</td>"
            f"<td>{short_name}</td>"
            f"<td>{letter}</td>"
            f"<td>{team_id}</td>"
            f"<td>{logo_markup}</td>"
            "</tr>"
        )

    table_body = "\n".join(rows) if rows else "<tr><td colspan='5'>No teams available.</td></tr>"
    selected_title = (
        escape(selected_series_info.get("name", ""))
        if isinstance(selected_series_info, dict)
        else ""
    )

    return (
        "<!DOCTYPE html>"
        "<html lang='en'>"
        "<head>"
        "<meta charset='utf-8'/>"
        "<title>Teams</title>"
        "<style>"
        "body{font-family:Arial,sans-serif;margin:2rem;background:#f5f5f5;}"
        "h1{margin-bottom:1rem;}"
        "form{margin-bottom:1rem;}"
        "select{padding:0.5rem;font-size:1rem;}"
        "button{padding:0.5rem 1rem;margin-left:0.5rem;}"
        "table{width:100%;border-collapse:collapse;background:#fff;"
        "box-shadow:0 1px 3px rgba(0,0,0,0.1);border-radius:8px;overflow:hidden;}"
        "th,td{padding:0.75rem;border-bottom:1px solid #eee;text-align:left;}"
        "th{background:#005a9c;color:#fff;}"
        "tr:last-child td{border-bottom:none;}"
        ".team-logo{max-height:40px;}"
        "nav a{margin-right:1rem;}"
        "</style>"
        "</head>"
        "<body>"
        f"{_NAV_HTML}"
        "<h1>Teams</h1>"
        "<form method='get' action='/teams'>"
        "<label for='series-select'>Choose a series:</label>"
        f"<select id='series-select' name='series'>{''.join(options_markup)}</select>"
        "<button type='submit'>Show Teams</button>"
        "</form>"
        f"<h2>{selected_title}</h2>"
        "<table>"
        "<thead><tr><th>Name</th><th>Short Name</th><th>Letter</th><th>Team ID</th><th>Logo</th></tr></thead>"
        f"<tbody>{table_body}</tbody>"
        "</table>"
        "</body>"
        "</html>"
    )






def _compute_series_stats(document: Dict[str, Any], series_uuid: str) -> Dict[str, Dict[str, int]]:
    match_states = document.get("matchStates") or {}
    stats: Dict[str, Dict[str, int]] = {}

    for day in document.get("matchDays") or []:
        for match in day.get("matches", []):
            if match.get("matchSeries") != series_uuid:
                continue
            team1_id = match.get("team1")
            team2_id = match.get("team2")
            match_uuid = match.get("id")
            if not match_uuid or not team1_id or not team2_id:
                continue
            state = match_states.get(match_uuid) or {}
            if not state.get("finished") and not state.get("finalized"):
                continue
            set_points = state.get("setPoints") or {}
            team1_sets = set_points.get("team1")
            team2_sets = set_points.get("team2")
            if not isinstance(team1_sets, int) or not isinstance(team2_sets, int):
                continue

            team1_stats = stats.setdefault(team1_id, {"played": 0, "wins": 0, "losses": 0, "points": 0})
            team2_stats = stats.setdefault(team2_id, {"played": 0, "wins": 0, "losses": 0, "points": 0})

            team1_stats["played"] += 1
            team2_stats["played"] += 1

            if team1_sets == team2_sets:
                continue

            winner_id = team1_id if team1_sets > team2_sets else team2_id
            loser_id = team2_id if winner_id == team1_id else team1_id
            winner_sets = max(team1_sets, team2_sets)
            loser_sets = min(team1_sets, team2_sets)

            stats[winner_id]["wins"] += 1
            stats[loser_id]["losses"] += 1

            winner_points = 3 if loser_sets <= 1 else 2
            loser_points = 1 if loser_sets == 2 else 0

            stats[winner_id]["points"] += winner_points
            stats[loser_id]["points"] += loser_points

    return stats



def _filter_matches_for_today(document: Dict[str, Any]) -> List[Dict[str, Any]]:
    today = datetime.now(timezone.utc).date()
    match_states = document.get("matchStates") or {}
    games: List[Dict[str, Any]] = []

    for day in document.get("matchDays") or []:
        for match in day.get("matches", []):
            scheduled_ms = match.get("date")
            if not isinstance(scheduled_ms, (int, float)):
                continue
            scheduled_dt = datetime.fromtimestamp(scheduled_ms / 1000, tz=timezone.utc)
            if scheduled_dt.date() != today:
                continue

            match_uuid = match.get("id")
            state = match_states.get(match_uuid, {}) if match_uuid else {}
            raw_sets = []
            for match_set in state.get("matchSets") or []:
                set_number = match_set.get("setNumber")
                set_score = match_set.get("setScore") or {}
                team1_points = set_score.get("team1")
                team2_points = set_score.get("team2")
                if not (
                    isinstance(set_number, int)
                    and isinstance(team1_points, int)
                    and isinstance(team2_points, int)
                ):
                    continue
                raw_sets.append(
                    {
                        "number": set_number,
                        "team1": team1_points,
                        "team2": team2_points,
                    }
                )

            raw_sets.sort(key=lambda entry: entry["number"])

            games.append(
                {
                    "matchUuid": match_uuid,
                    "seriesUuid": match.get("matchSeries"),
                    "scheduledIso": scheduled_dt.isoformat(),
                    "team1": match.get("teamDescription1"),
                    "team2": match.get("teamDescription2"),
                    "finished": state.get("finished"),
                    "finalized": state.get("finalized"),
                    "sets": raw_sets,
                }
            )

    games.sort(key=lambda entry: entry.get("scheduledIso") or "")
    return games



def render_live_games_html(payload: str) -> str:
    document = json.loads(payload)
    series_mapping = extract_series_mapping(payload)
    games = _filter_matches_for_today(document)

    items: List[str] = []
    for game in games:
        series_name = series_mapping.get(game.get("seriesUuid"), "")
        team1 = escape(game.get("team1", "Unknown"))
        team2 = escape(game.get("team2", "Unknown"))
        scheduled = escape(game.get("scheduledIso") or "Unknown time")
        status = _render_status(game)
        sets = game.get("sets") or []
        set_items = []
        for match_set in sets:
            number = match_set.get("number")
            team1_points = match_set.get("team1")
            team2_points = match_set.get("team2")
            set_items.append(
                f"<li>Set {number}: {team1_points}-{team2_points}</li>"
            )
        if set_items:
            sets_markup = (
                f"<div class='match-sets'>Sets played: {len(sets)}</div>"
                f"<ul class='set-list'>{''.join(set_items)}</ul>"
            )
        else:
            sets_markup = "<div class='match-sets'>Sets played: 0</div>"
        items.append(
            "<li>"
            f"<div class='match-series'>{escape(series_name)}</div>"
            f"<div class='match-teams'>{team1} vs {team2}</div>"
            f"<div class='match-time'>{scheduled}</div>"
            f"<div class='match-status'>{status}</div>"
            f"{sets_markup}"
            "</li>"
        )

    if not items:
        items.append("<li>No games scheduled for today.</li>")

    list_markup = "\n".join(items)
    return (
        "<!DOCTYPE html>"
        "<html lang='en'>"
        "<head>"
        "<meta charset='utf-8'/>"
        "<title>Live Games</title>"
        "<style>"
        "body{font-family:Arial,sans-serif;margin:2rem;background:#f5f5f5;}"
        "h1{margin-bottom:1rem;}"
        "ul{list-style:none;padding:0;}"
        "li{background:#fff;padding:1rem;margin-bottom:1rem;border-radius:8px;"
        "box-shadow:0 1px 3px rgba(0,0,0,0.1);}"
        ".match-series{font-weight:bold;color:#005a9c;margin-bottom:0.25rem;}"
        ".match-teams{font-size:1.1rem;margin-bottom:0.25rem;}"
        ".match-time{color:#555;margin-bottom:0.25rem;}"
        ".match-status{font-size:0.9rem;color:#777;}"
        ".match-sets{margin-top:0.5rem;color:#333;}"
        ".set-list{list-style:none;padding:0;margin:0.5rem 0 0;display:flex;flex-wrap:wrap;gap:0.5rem;}"
        ".set-list li{background:#e7effa;padding:0.25rem 0.5rem;border-radius:4px;}"
        "nav a{margin-right:1rem;}"
        "</style>"
        "</head>"
        "<body>"
        f"{_NAV_HTML}"
        "<h1>Live Games Today</h1>"
        f"<ul>{list_markup}</ul>"
        "</body>"
        "</html>"
    )

def render_rankings_html(payload: str, selected_series_uuid: Optional[str] = None) -> str:
    """Render an HTML page with a series dropdown and rankings table."""
    document = json.loads(payload)
    match_series = document.get("matchSeries") or {}
    series_list = extract_series_list(payload)

    if not series_list:
        selected_series_uuid = None
    elif selected_series_uuid not in match_series:
        selected_series_uuid = series_list[0]["uuid"]

    options_markup: List[str] = []
    for series in series_list:
        uuid = series.get("uuid", "")
        name = series.get("name") or "Unnamed series"
        selected_attr = " selected" if uuid == selected_series_uuid else ""
        options_markup.append(
            f"<option value='{escape(uuid)}'{selected_attr}>{escape(name)}</option>"
        )

    selected_series_info = (
        match_series.get(selected_series_uuid) if selected_series_uuid else None
    )
    rankings = []
    if isinstance(selected_series_info, dict):
        rankings = (
            selected_series_info.get("rankings", {}).get("fullRankings") or []
        )

    stats = _compute_series_stats(document, selected_series_uuid) if selected_series_uuid else {}

    rows: List[str] = []
    for entry in rankings:
        position = entry.get("rankingPosition")
        team = entry.get("team") or {}
        team_id = team.get("id")
        score_details = entry.get("scoreDetails") or {}
        team_stats = stats.get(team_id, {"played": 0, "wins": 0, "losses": 0, "points": 0})

        known_played = int(team_stats.get("played", 0))
        known_wins = int(team_stats.get("wins", 0))
        known_losses = int(team_stats.get("losses", 0))
        known_points = int(team_stats.get("points", 0))

        played_value = score_details.get("matchesPlayed")
        played = int(played_value) if isinstance(played_value, int) else known_played
        win_score = int(score_details.get("winScore", 0))

        wins = known_wins
        losses = known_losses

        remaining_matches = max(0, played - known_played)
        remaining_points = max(0, win_score - known_points)

        if remaining_matches and team_id:
            assigned = False
            for additional_wins in range(remaining_matches, -1, -1):
                additional_losses = remaining_matches - additional_wins
                min_points = 2 * additional_wins
                max_points = 3 * additional_wins + additional_losses
                if min_points <= remaining_points <= max_points:
                    wins += additional_wins
                    losses += additional_losses
                    assigned = True
                    break
            if not assigned:
                losses += remaining_matches

        total_recorded = wins + losses
        if total_recorded > played:
            losses = max(0, played - wins)
        elif total_recorded < played:
            losses += played - total_recorded

        team_name = escape(team.get("name", "Unknown team"))
        logo = escape(team.get("logoImage200", ""))
        logo_markup = (
            f"<img src='{logo}' alt='{team_name} logo' class='team-logo'/>"
            if logo
            else ""
        )
        rows.append(
            "<tr>"
            f"<td>{position if position is not None else ''}</td>"
            f"<td>{team_name}</td>"
            f"<td>{played}</td>"
            f"<td>{wins}</td>"
            f"<td>{losses}</td>"
            f"<td>{logo_markup}</td>"
            "</tr>"
        )

    table_body = "\n".join(rows) if rows else "<tr><td colspan='6'>No rankings available.</td></tr>"
    selected_title = (
        escape(selected_series_info.get("name", ""))
        if isinstance(selected_series_info, dict)
        else ""
    )

    return (
        "<!DOCTYPE html>"
        "<html lang='en'>"
        "<head>"
        "<meta charset='utf-8'/>"
        "<title>Rankings</title>"
        "<style>"
        "body{font-family:Arial,sans-serif;margin:2rem;background:#f5f5f5;}"
        "h1{margin-bottom:1rem;}"
        "form{margin-bottom:1rem;}"
        "select{padding:0.5rem;font-size:1rem;}"
        "button{padding:0.5rem 1rem;margin-left:0.5rem;}"
        "table{width:100%;border-collapse:collapse;background:#fff;"
        "box-shadow:0 1px 3px rgba(0,0,0,0.1);border-radius:8px;overflow:hidden;}"
        "th,td{padding:0.75rem;border-bottom:1px solid #eee;text-align:left;}"
        "th{background:#005a9c;color:#fff;}"
        "tr:last-child td{border-bottom:none;}"
        ".team-logo{max-height:40px;}"
        "nav a{margin-right:1rem;}"
        "</style>"
        "</head>"
        "<body>"
        f"{_NAV_HTML}"
        "<h1>Rankings</h1>"
        "<form method='get' action='/rankings'>"
        "<label for='series-select'>Choose a series:</label>"
        f"<select id='series-select' name='series'>{''.join(options_markup)}</select>"
        "<button type='submit'>Show Rankings</button>"
        "</form>"
        f"<h2>{selected_title}</h2>"
        "<table>"
        "<thead><tr><th>Rank</th><th>Team</th><th>Played</th><th>Wins</th><th>Losses</th><th>Logo</th></tr></thead>"
        f"<tbody>{table_body}</tbody>"
        "</table>"
        "</body>"
        "</html>"
    )

def _epoch_ms_to_iso(epoch_ms: Any) -> str | None:
    if not isinstance(epoch_ms, (int, float)):
        return None
    return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).isoformat()


def _render_status(game: Dict[str, Any]) -> str:
    if game.get("finished"):
        return "Finished"
    if game.get("finalized"):
        return "Finalized"
    return "Scheduled"
