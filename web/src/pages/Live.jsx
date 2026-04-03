import { useEffect, useMemo, useState } from "react";
import {
  Box,
  Chip,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Typography
} from "@mui/material";
import { useParams } from "react-router-dom";
import { fetchMatchesByCompetitionUuid } from "../api/api.js";
import { layout } from "../components/layout.js";

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
    return {};
  }

  const isHigher =
    (side === "left" && leftValue > rightValue) ||
    (side === "right" && rightValue > leftValue);

  return {
    bgcolor: isHigher ? "rgba(178, 232, 187, 0.6)" : "rgba(244, 199, 199, 0.7)",
    borderRadius: 1,
    px: 0.75,
    py: 0.25,
    fontWeight: isHigher ? 700 : 400
  };
}

function getActiveSetStyles(matchState, setIndex) {
  const isInProgress = matchState?.started && !matchState?.finished;
  const lastSetIndex = (matchState?.matchSets?.length ?? 0) - 1;

  if (isInProgress && setIndex === lastSetIndex) {
    return {
      bgcolor: "#e5e7eb",
      borderRadius: 1,
      px: 0.75,
      py: 0.25
    };
  }

  return {};
}

function isActiveSet(matchState, setIndex) {
  const isInProgress = matchState?.started && !matchState?.finished;
  const lastSetIndex = (matchState?.matchSets?.length ?? 0) - 1;

  return isInProgress && setIndex === lastSetIndex;
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

function getStatusChip(matchState) {
  if (!matchState?.started) {
    return {
      label: "SCHEDULED",
      sx: {
        bgcolor: "#fef3c7",
        color: "#c2410c"
      }
    };
  }

  if (matchState.finished) {
    return {
      label: "FINISHED",
      sx: {
        bgcolor: "#e5e7eb",
        color: "#4b5563"
      }
    };
  }

  return {
    label: "IN PROGRESS",
    sx: {
      bgcolor: "#d32f2f",
      color: "#ffffff"
    }
  };
}

function MatchRow({ match }) {
  const team1SetPoints = getTeamSetPoints(match.matchState, "left");
  const team2SetPoints = getTeamSetPoints(match.matchState, "right");
  const totalSetPoints = getTotalSetPoints(match.matchState);
  const winnerSide = getWinnerSide(match.matchState);
  const statusChip = getStatusChip(match.matchState);
  const isInProgress = match.matchState?.started && !match.matchState?.finished;
  const servingTeam = isInProgress ? match.matchState?.serving : null;

  return (
    <Box
      sx={{
        p: layout.padding.card,
        borderRadius: layout.radius.surface,
        bgcolor: "background.paper",
        display: "grid",
        gap: layout.gap.surface
      }}
    >
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "flex-start", sm: "center" }}
        spacing={0.5}
      >
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
          <Typography sx={{ fontWeight: 600, color: "rgba(26, 21, 18, 0.45)" }}>
            {formatMatchDate(match.date)}
          </Typography>
          {statusChip && (
            <Chip
              label={statusChip.label}
              size="small"
              sx={{
                height: 20,
                fontSize: "0.6875rem",
                fontWeight: 700,
                "& .MuiChip-label": {
                  px: 0.75
                },
                ...statusChip.sx
              }}
            />
          )}
        </Stack>
        <Typography sx={{ color: "rgba(26, 21, 18, 0.45)" }}>
          {match.matchSeriesData?.name ?? "Unknown competition"}
        </Typography>
      </Stack>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 2fr) 32px minmax(0, 1fr)",
          alignItems: "center",
          columnGap: 1.5
        }}
      >
        <Typography
          sx={{
            fontWeight: winnerSide === "team1" || servingTeam === "team1" ? 700 : 500,
            display: "inline-flex",
            alignItems: "center",
            gap: 0.75
          }}
        >
          <Box component="span">{match.teamDescription1}</Box>
          {servingTeam === "team1" && (
            <Box
              component="img"
              src="/volleyball.png"
              alt=""
              aria-hidden="true"
              sx={{ width: 14, height: 14, flexShrink: 0 }}
            />
          )}
        </Typography>
        <Typography
          variant="body2"
          sx={{
            width: 32,
            textAlign: "center",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: servingTeam === "team1" || winnerSide === "team1" ? 700 : 500
          }}
        >
          {totalSetPoints.leftPoints}
        </Typography>
        <Stack direction="row" spacing={1} justifyContent="flex-end" sx={{ justifySelf: "end" }}>
          {team1SetPoints.map((points, index) => {
            const opposingPoints = team2SetPoints[index] ?? "-";
            const activeSet = isActiveSet(match.matchState, index);

            return (
              <Typography
                key={`${match.id}-team1-set-${index + 1}`}
                variant="body2"
                color="text.secondary"
                sx={{
                  width: 32,
                  textAlign: "center",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  ...getActiveSetStyles(match.matchState, index),
                  ...(activeSet && servingTeam === "team1"
                    ? {
                        fontWeight: 700,
                        border: "1px solid #4b5563"
                      }
                    : {}),
                  ...(!activeSet ? getSetPointStyles(points, opposingPoints, "left") : {})
                }}
              >
                {points}
              </Typography>
            );
          })}
        </Stack>
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 2fr) 32px minmax(0, 1fr)",
          alignItems: "center",
          columnGap: 1.5
        }}
      >
        <Typography
          sx={{
            fontWeight: winnerSide === "team2" || servingTeam === "team2" ? 700 : 500,
            display: "inline-flex",
            alignItems: "center",
            gap: 0.75
          }}
        >
          <Box component="span">{match.teamDescription2}</Box>
          {servingTeam === "team2" && (
            <Box
              component="img"
              src="/volleyball.png"
              alt=""
              aria-hidden="true"
              sx={{ width: 14, height: 14, flexShrink: 0 }}
            />
          )}
        </Typography>
        <Typography
          variant="body2"
          sx={{
            width: 32,
            textAlign: "center",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: servingTeam === "team2" || winnerSide === "team2" ? 700 : 500
          }}
        >
          {totalSetPoints.rightPoints}
        </Typography>
        <Stack direction="row" spacing={1} justifyContent="flex-end" sx={{ justifySelf: "end" }}>
          {team2SetPoints.map((points, index) => {
            const opposingPoints = team1SetPoints[index] ?? "-";
            const activeSet = isActiveSet(match.matchState, index);

            return (
              <Typography
                key={`${match.id}-team2-set-${index + 1}`}
                variant="body2"
                color="text.secondary"
                sx={{
                  width: 32,
                  textAlign: "center",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  ...getActiveSetStyles(match.matchState, index),
                  ...(activeSet && servingTeam === "team2"
                    ? {
                        fontWeight: 700,
                        border: "1px solid #4b5563"
                      }
                    : {}),
                  ...(!activeSet ? getSetPointStyles(opposingPoints, points, "right") : {})
                }}
              >
                {points}
              </Typography>
            );
          })}
        </Stack>
      </Box>
    </Box>
  );
}

function MatchSection({ title, matches, emptyText }) {
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
          {matches.map((match) => (
            <MatchRow key={match.id} match={match} />
          ))}
        </Stack>
      )}
    </Paper>
  );
}

export default function Live() {
  const { competitionUuid } = useParams();
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedTeamId, setSelectedTeamId] = useState("all");

  useEffect(() => {
    let isMounted = true;
    let isInitialLoad = true;

    async function loadMatches() {
      if (!competitionUuid) {
        if (isMounted) {
          setMatches([]);
          setError("Missing competition uuid");
          setLoading(false);
        }
        return;
      }

      if (isInitialLoad) {
        setLoading(true);
        setError("");
      }

      try {
        const nextMatches = await fetchMatchesByCompetitionUuid(competitionUuid);

        if (isMounted) {
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
    const intervalId = window.setInterval(loadMatches, 1000);

    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
    };
  }, [competitionUuid]);

  const liveMatches = useMemo(
    () => matches.filter((match) => match.matchState?.started && !match.matchState?.finished),
    [matches]
  );
  const upcomingMatches = useMemo(
    () => matches.filter((match) => !match.matchState?.started),
    [matches]
  );
  const finishedMatches = useMemo(
    () => matches.filter((match) => match.matchState?.finished),
    [matches]
  );
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

    return matchList.filter(
      (match) => match.team1 === selectedTeamId || match.team2 === selectedTeamId
    );
  };

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
            emptyText="No matches are currently in progress."
          />
          <MatchSection
            title="Upcoming Matches"
            matches={filteredUpcomingMatches}
            emptyText="No upcoming matches found."
          />
          <MatchSection
            title="Finished Matches"
            matches={filteredFinishedMatches}
            emptyText="No finished matches found."
          />
        </Box>
      )}
    </Box>
  );
}
