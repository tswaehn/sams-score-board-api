import { useEffect, useMemo, useState } from "react";
import {
  Box,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Typography
} from "@mui/material";
import { useParams } from "react-router-dom";
import { fetchMatchesBySeriesUuid, useIsMobile } from "../api/api.js";
import { layout } from "../components/layout.js";
import { MatchResultCard } from "../components/matchResultCard.jsx";
import { getCompetitionStatusChip } from "../components/stateChip.jsx";

function formatMatchDate(timestamp) {
  return new Intl.DateTimeFormat("de-DE", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(timestamp));
}

function getSetPointStyles(leftPoints, rightPoints, side) {
  const leftValue = Number(leftPoints);
  const rightValue = Number(rightPoints);

  if (Number.isNaN(leftValue) || Number.isNaN(rightValue) || leftValue === rightValue) {
    return "default";
  }

  const isHigher =
    (side === "left" && leftValue > rightValue) ||
    (side === "right" && rightValue > leftValue);

  return isHigher ? "won" : "lost";
}

function getActiveSetState(matchState, setIndex, servingTeam, teamKey) {
  const isInProgress = matchState?.started && !matchState?.finished;
  const lastSetIndex = (matchState?.matchSets?.length ?? 0) - 1;

  if (isInProgress && setIndex === lastSetIndex) {
    return servingTeam === teamKey ? "activeServing" : "active";
  }

  return null;
}

function getTeamSetPoints(matchState, side) {
  const sets = matchState?.matchSets ?? [];

  return sets.map((set) => {
    const points = side === "left" ? set?.setScore?.team1 : set?.setScore?.team2;
    return points ?? "-";
  });
}

function getTotalSetPoints(matchState) {
  return {
    leftPoints: matchState?.setPoints?.team1 ?? "-",
    rightPoints: matchState?.setPoints?.team2 ?? "-"
  };
}

function getWinnerSide(matchState) {
  if (!matchState?.finished) {
    return null;
  }

  const leftPoints = matchState?.setPoints?.team1 ?? 0;
  const rightPoints = matchState?.setPoints?.team2 ?? 0;

  if (leftPoints === rightPoints) {
    return null;
  }

  return leftPoints > rightPoints ? "team1" : "team2";
}

function getCompetitionResultRows(match) {
  const team1SetPoints = getTeamSetPoints(match.matchState, "left");
  const team2SetPoints = getTeamSetPoints(match.matchState, "right");
  const totalSetPoints = getTotalSetPoints(match.matchState);
  const winnerSide = getWinnerSide(match.matchState);
  const isInProgress = match.matchState?.started && !match.matchState?.finished;
  const servingTeam = isInProgress ? match.matchState?.serving : null;

  function getServingAdornment(teamKey) {
    if (servingTeam !== teamKey) {
      return null;
    }

    return (
      <Box
        component="img"
        src="/volleyball.png"
        alt=""
        aria-hidden="true"
        sx={{ width: 14, height: 14, flexShrink: 0 }}
      />
    );
  }

  return [
    {
      key: `${match.id}-team1`,
      teamName: match.teamDescription1,
      isWinner: winnerSide === "team1",
      isHighlighted: winnerSide === "team1" || servingTeam === "team1",
      labelAdornment: getServingAdornment("team1"),
      totalSetPoints: totalSetPoints.leftPoints,
      setPoints: team1SetPoints,
      opponentSetPoints: team2SetPoints,
      setPointStates: team1SetPoints.map((points, index) => {
        const activeState = getActiveSetState(match.matchState, index, servingTeam, "team1");
        return activeState ?? getSetPointStyles(points, team2SetPoints[index] ?? "-", "left");
      }),
      side: "left"
    },
    {
      key: `${match.id}-team2`,
      teamName: match.teamDescription2,
      isWinner: winnerSide === "team2",
      isHighlighted: winnerSide === "team2" || servingTeam === "team2",
      labelAdornment: getServingAdornment("team2"),
      totalSetPoints: totalSetPoints.rightPoints,
      setPoints: team2SetPoints,
      opponentSetPoints: team1SetPoints,
      setPointStates: team2SetPoints.map((points, index) => {
        const activeState = getActiveSetState(match.matchState, index, servingTeam, "team2");
        return activeState ?? getSetPointStyles(team1SetPoints[index] ?? "-", points, "right");
      }),
      side: "right"
    }
  ];
}

function CompetitionMatchRow({ match, isMobile }) {
  const statusChip = getCompetitionStatusChip(match.matchState);

  return (
    <MatchResultCard
      dateLabel={formatMatchDate(match.date)}
      locationLabel={match.matchSeriesData?.name ?? "Unknown series"}
      statusChip={statusChip}
      rows={getCompetitionResultRows(match)}
      compact={isMobile}
      showBallPoints={false}
    />
  );
}

function MatchSection({ title, matches, emptyText, renderMatch }) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: layout.padding.surface,
        borderRadius: layout.radius.surface,
        border: "1px solid rgba(20, 17, 15, 0.08)",
        bgcolor: "background.paper",
        display: "grid",
        gap: layout.gap.surface
      }}
    >
      <Typography variant="h6" sx={{ fontWeight: 700 }}>
        {title}
      </Typography>

      {matches.length === 0 ? (
        <Typography color="text.secondary">{emptyText}</Typography>
      ) : (
        <Stack spacing={layout.gap.cardList}>
          {matches.map((match) => renderMatch(match))}
        </Stack>
      )}
    </Paper>
  );
}

export default function EntityLive({ expectedEntityType }) {
  const { competitionUuid, leagueUuid } = useParams();
  const isMobile = useIsMobile();
  const [entityType, setEntityType] = useState(expectedEntityType ?? "competition");
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedTeamId, setSelectedTeamId] = useState("all");
  const seriesUuid = expectedEntityType === "competition" ? competitionUuid : leagueUuid;

  useEffect(() => {
    let isMounted = true;
    let isInitialLoad = true;

    async function loadMatches() {
      if (isInitialLoad) {
        setLoading(true);
        setError("");
      }

      try {
        if (!seriesUuid) {
          throw new Error(`Missing ${expectedEntityType ?? "live"} uuid`);
        }

        const nextMatches = await fetchMatchesBySeriesUuid(seriesUuid);

        if (isMounted) {
          setEntityType(expectedEntityType ?? "competition");
          setMatches(nextMatches);
          setError("");
          setLoading(false);
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

    loadMatches();
    const intervalId = window.setInterval(
      loadMatches,
      2000
    );

    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
    };
  }, [expectedEntityType, seriesUuid]);

  const teams = useMemo(() => {
    const teamMap = new Map();

    matches.forEach((match) => {
      if (match.team1 && match.teamDescription1) {
        teamMap.set(match.team1, {
          id: match.team1,
          name: match.teamDescription1
        });
      }

      if (match.team2 && match.teamDescription2) {
        teamMap.set(match.team2, {
          id: match.team2,
          name: match.teamDescription2
        });
      }
    });

    return Array.from(teamMap.values()).sort((left, right) => left.name.localeCompare(right.name));
  }, [matches]);

  const filterMatchesByTeam = (matchList) => {
    if (selectedTeamId === "all") {
      return matchList;
    }

    return matchList.filter((match) => match.team1 === selectedTeamId || match.team2 === selectedTeamId);
  };

  const liveMatches = useMemo(() => {
    return matches.filter((match) => match.matchState?.started && !match.matchState?.finished);
  }, [matches]);

  const upcomingMatches = useMemo(() => {
    return matches.filter((match) => !match.matchState?.started);
  }, [matches]);

  const finishedMatches = useMemo(() => {
    return matches.filter((match) => match.matchState?.finished);
  }, [matches]);

  const filteredLiveMatches = filterMatchesByTeam(liveMatches);
  const filteredUpcomingMatches = filterMatchesByTeam(upcomingMatches);
  const filteredFinishedMatches = filterMatchesByTeam(finishedMatches);

  return (
    <Box sx={{ display: "grid", gap: layout.gap.page }}>
      {loading && <Typography color="text.secondary">Loading live feed...</Typography>}
      {error && (
        <Typography color="error" sx={{ fontWeight: 600 }}>
          {error}
        </Typography>
      )}

      {!loading && !error && (
        <Box sx={{ display: "grid", gap: layout.gap.page }}>
          <Paper
            elevation={0}
            sx={{
              p: layout.padding.surface,
              borderRadius: layout.radius.surface,
              border: "1px solid rgba(20, 17, 15, 0.08)",
              bgcolor: "#ffffff"
            }}
          >
            <Stack spacing={layout.gap.surface} alignItems="center">
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Wähle dein Team
              </Typography>
              <FormControl size="small" sx={{ minWidth: 240, width: "100%", maxWidth: 360 }}>
                <InputLabel id="live-team-filter-label">Team</InputLabel>
                <Select
                  labelId="live-team-filter-label"
                  value={selectedTeamId}
                  label="Team"
                  onChange={(event) => setSelectedTeamId(event.target.value)}
                  sx={{ bgcolor: "#ffffff" }}
                >
                  <MenuItem value="all">All teams</MenuItem>
                  {teams.map((team) => (
                    <MenuItem key={team.id} value={team.id}>
                      {team.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Stack>
          </Paper>

          <MatchSection
            title="Live"
            matches={filteredLiveMatches}
            emptyText={
              entityType === "competition"
                ? "No matches are currently in progress."
                : "No league matches are currently in progress."
            }
            renderMatch={(match) => <CompetitionMatchRow key={match.id} match={match} isMobile={isMobile} />}
          />

          <MatchSection
            title="Upcoming Matches"
            matches={filteredUpcomingMatches}
            emptyText="No upcoming matches found."
            renderMatch={(match) => <CompetitionMatchRow key={match.id} match={match} isMobile={isMobile} />}
          />

          <MatchSection
            title="Finished Matches"
            matches={filteredFinishedMatches}
            emptyText="No finished matches found."
            renderMatch={(match) => <CompetitionMatchRow key={match.id} match={match} isMobile={isMobile} />}
          />
        </Box>
      )}
    </Box>
  );
}
