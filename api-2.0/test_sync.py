from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from database import Database
from sync import HistoricalSync


HISTORIC = "00000000-0000-0000-0000-000000000001"
CURRENT = "00000000-0000-0000-0000-000000000002"
COMPETITION = "00000000-0000-0000-0000-000000000003"
LEAGUE = "00000000-0000-0000-0000-000000000004"
ASSOCIATION = "00000000-0000-0000-0000-000000000005"
TEAM = "00000000-0000-0000-0000-000000000006"


class FakeUpstream:
    pending_count = 0

    def __init__(self) -> None:
        self.calls: list[str] = []

    def fetch(self, endpoint: str, *, priority: int):
        self.calls.append(endpoint)
        base = endpoint.split("?", 1)[0]
        if base == "seasons":
            return {"content": [{"uuid": HISTORIC, "name": "Past", "startDate": "2024-01-01", "currentSeason": False}, {"uuid": CURRENT, "name": "Now", "startDate": "2025-01-01", "currentSeason": True}]}
        if base == "competitions" and CURRENT in endpoint:
            return {"content": []}
        if base == "competitions":
            return {"content": [{"uuid": COMPETITION}]}
        if base == "leagues" and CURRENT in endpoint:
            return {"content": []}
        if base == "leagues":
            return {"content": [{"uuid": LEAGUE}]}
        if base == f"competitions/{COMPETITION}":
            return {"uuid": COMPETITION, "name": "Cup", "gender": "M", "_links": {"season": {"href": f"https://x/api/v2/seasons/{HISTORIC}"}, "association": {"href": f"https://x/api/v2/associations/{ASSOCIATION}"}}}
        if base == f"leagues/{LEAGUE}":
            return {"uuid": LEAGUE, "name": "League", "seasonUuid": HISTORIC, "associationUuid": ASSOCIATION}
        if base in {f"competitions/{COMPETITION}/teams", f"leagues/{LEAGUE}/teams"}:
            return {"content": [{"uuid": TEAM}]}
        if base == f"teams/{TEAM}":
            return {"uuid": TEAM, "name": "Team", "associationUuid": ASSOCIATION}
        if base == f"associations/{ASSOCIATION}":
            return {"uuid": ASSOCIATION, "name": "Club"}
        raise AssertionError(base)


class HistoricalSyncTest(unittest.TestCase):
    def test_syncs_seasons_then_entities_by_season(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(str(Path(directory) / "mirror.sqlite3"))
            database.initialize()
            upstream = FakeUpstream()
            HistoricalSync(database, upstream).sync_once()

            self.assertTrue(upstream.calls[0].startswith("seasons?"))
            self.assertTrue(any(call.startswith(f"competitions?season={HISTORIC}") for call in upstream.calls))
            self.assertTrue(any(call.startswith(f"competitions?season={CURRENT}") for call in upstream.calls))
            self.assertLess(
                upstream.calls.index(f"competitions?season={CURRENT}&page=0&size=100"),
                upstream.calls.index(f"competitions?season={HISTORIC}&page=0&size=100"),
            )
            competitions = database.list_entities("competition")
            self.assertEqual([COMPETITION], [item["uuid"] for item in competitions])
            self.assertFalse(competitions[0]["currentSeason"])
            self.assertEqual([LEAGUE], [item["uuid"] for item in database.list_entities("league")])
            self.assertEqual({"seasons": 2, "competitions": 1, "leagues": 1, "teams": 1, "associations": 1}, database.status())

            upstream.calls.clear()
            HistoricalSync(database, upstream).sync_once()
            self.assertNotIn(f"teams/{TEAM}", upstream.calls)
            self.assertNotIn(f"associations/{ASSOCIATION}", upstream.calls)
            self.assertNotIn(f"seasons/{HISTORIC}", upstream.calls)
            self.assertNotIn(f"competitions/{COMPETITION}/teams?page=0&size=100", upstream.calls)
            self.assertNotIn(f"leagues/{LEAGUE}/teams?page=0&size=100", upstream.calls)
            self.assertNotIn(f"competitions/{COMPETITION}", upstream.calls)
            self.assertNotIn(f"leagues/{LEAGUE}", upstream.calls)

            upstream.calls.clear()
            HistoricalSync(database, upstream).sync_once(force=True)
            self.assertIn(f"competitions/{COMPETITION}", upstream.calls)
            self.assertIn(f"leagues/{LEAGUE}", upstream.calls)


if __name__ == "__main__":
    unittest.main()
