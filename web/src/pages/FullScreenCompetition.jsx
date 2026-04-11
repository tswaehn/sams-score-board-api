import { useEffect, useMemo, useState } from "react";
import { Box, Typography } from "@mui/material";
import { useLocation } from "react-router-dom";
import { fetchJson, useIsMobile } from "../api/api.js";
import { layout } from "../components/layout.js";
import FullScreenRanking from "../components/FullScreenRanking.jsx";

function getRankingRows(rankings, rankingName) {
  const groupRankings = rankings[rankingName] ?? {};

  return Object.entries(groupRankings)
    .sort(([left], [right]) => Number(left) - Number(right))
    .map(([rank, entry]) => ({
      rank,
      ...entry
    }));
}

function getSortedMatches(group) {
  return Object.values(group?.matches ?? {}).sort((left, right) => {
    const leftDateTime = `${left.date ?? ""}T${left.time ?? "00:00"}`;
    const rightDateTime = `${right.date ?? ""}T${right.time ?? "00:00"}`;

    return leftDateTime.localeCompare(rightDateTime);
  });
}

export default function FullScreenCompetition() {
  const location = useLocation();
  const isMobile = useIsMobile();
  const [matchGroups, setMatchGroups] = useState([]);
  const [rankings, setRankings] = useState({});
  const [teams, setTeams] = useState([]);
  const [displayMode, setDisplayMode] = useState("ranking");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;
    let isInitialLoad = true;

    async function loadCompetitionOverview() {
      if (isInitialLoad) {
        setLoading(true);
        setError("");
      }

      try {
        const data = await fetchJson("/api/plan");

        if (isMounted) {
          if (data.entityType !== "competition") {
            setError(`Unexpected entity type: ${data.entityType}`);
            setLoading(false);
            return;
          }

          setMatchGroups(data.matchGroups ?? []);
          setRankings(data.rankings ?? {});
          setTeams(data.teams ?? []);
          setLoading(false);
          setError("");
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message);
          setLoading(false);
        }
      } finally {
        isInitialLoad = false;
      }
    }

    loadCompetitionOverview();
    const intervalId = window.setInterval(loadCompetitionOverview, 20000);

    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
    };
  }, [location.pathname]);

  const teamByName = useMemo(() => {
    const map = new Map();

    teams.forEach((team) => {
      map.set(team.name, team);
    });

    return map;
  }, [teams]);

  const teamByUuid = useMemo(() => {
    const map = new Map();

    teams.forEach((team) => {
      map.set(team.uuid, team);
    });

    return map;
  }, [teams]);

  const stageRankings = useMemo(() => {
    return matchGroups.map((group) => ({
      group,
      rankingRows: getRankingRows(rankings, group.name),
      matches: getSortedMatches(group)
    }));
  }, [matchGroups, rankings]);

  const stageRankingRows = useMemo(() => {
    if (stageRankings.length >= 8) {
      const rows = [];

      for (let index = 0; index < stageRankings.length; index += 6) {
        rows.push(stageRankings.slice(index, index + 6));
      }

      return rows;
    }

    const groupedByLevel = new Map();

    stageRankings.forEach((stageRanking) => {
      const level = stageRanking.group?.tourneyLevel ?? 0;
      const currentRow = groupedByLevel.get(level) ?? [];
      currentRow.push(stageRanking);
      groupedByLevel.set(level, currentRow);
    });

    return Array.from(groupedByLevel.entries())
      .sort(([leftLevel], [rightLevel]) => Number(leftLevel) - Number(rightLevel))
      .flatMap(([, items]) => {
        const rows = [];

        for (let index = 0; index < items.length; index += 6) {
          rows.push(items.slice(index, index + 6));
        }

        return rows;
      });
  }, [stageRankings]);

  const hasMatchDisplay = useMemo(() => {
    return stageRankings.some(({ matches }) => matches.length > 0);
  }, [stageRankings]);

  useEffect(() => {
    if (!hasMatchDisplay) {
      setDisplayMode("ranking");
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      setDisplayMode((currentMode) =>
        currentMode === "ranking" ? "matches" : "ranking"
      );
    }, 25000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [hasMatchDisplay]);

  return (
    <Box sx={{ display: "grid", gap: 1 }}>
      {loading && (
        <Typography color="text.secondary">Loading competition overview...</Typography>
      )}
      {error && (
        <Typography color="error" sx={{ fontWeight: 600 }}>
          {error}
        </Typography>
      )}

      {!loading && !error && (
        <Box
          sx={{
            display: "grid",
            gap: 1
          }}
        >
          {stageRankingRows.map((stageRankingRow, index) => (
            <Box
              key={`tourney-level-row-${index}`}
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "1fr",
                  md: `repeat(${Math.max(stageRankingRow.length, 1)}, minmax(0, 1fr))`
                },
                gap: 1,
                alignItems: "stretch"
              }}
            >
              {stageRankingRow.map(({ group, rankingRows, matches }) => (
                <FullScreenRanking
                  key={group.uuid}
                  group={group}
                  rankingRows={rankingRows}
                  matches={matches}
                  teamByName={teamByName}
                  teamByUuid={teamByUuid}
                  displayMode={displayMode}
                  compact={isMobile}
                />
              ))}
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
}
