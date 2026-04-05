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
import { useLocation, useParams } from "react-router-dom";
import { fetchJson, fetchMatchesByCompetitionUuid, useIsMobile } from "../api/api.js";
import { layout } from "../components/layout.js";
import { MatchResultCard } from "../components/matchResultCard.jsx";
import { getPlannedMatchStatusChip, StateChip } from "../components/stateChip.jsx";

function formatMatchDate(timestamp) {
  return new Intl.DateTimeFormat("de-DE", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(timestamp));
}

function formatLeagueMatchDate(date, time) {
  const raw = `${date ?? ""}${time ? `T${time}` : ""}`;
  const parsed = new Date(raw);

  if (Number.isNaN(parsed.getTime())) {
    return [date, time].filter(Boolean).join(" · ") || "Unknown time";
  }

  return new Intl.DateTimeFormat("de-DE", {
    dateStyle: "medium",
    timeStyle: time ? "short" : undefined
  }).format(parsed);
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

function getCompetitionStatusChip(matchState) {
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

function getLeagueStatusChip(match) {
  return getPlannedMatchStatusChip(match);
}

function getLeagueSetBallPoints(match, side) {
  const sets = match?.results?.sets ?? [];

  return sets.map((set) => {
    const [leftPoints = "-", rightPoints = "-"] = (set.ballPoints ?? "").split(":");
    return side === "left" ? leftPoints : rightPoints;
  });
}

function getLeagueResultRows(match) {
  const [leftSetPoints = "-", rightSetPoints = "-"] = (match.results?.setPoints ?? "").split(":");
  const [leftBallPoints = "-", rightBallPoints = "-"] = (match.results?.ballPoints ?? "").split(":");
  const team1SetPoints = getLeagueSetBallPoints(match, "left");
  const team2SetPoints = getLeagueSetBallPoints(match, "right");

  return [
    {
      key: `${match.uuid}-team1`,
      label: match.team1_name,
      isWinner: match.results?.winner === match.team1_uuid,
      totalSetPoints: leftSetPoints,
      setPoints: team1SetPoints,
      opponentSetPoints: team2SetPoints,
      ballPoints: leftBallPoints,
      side: "left"
    },
    {
      key: `${match.uuid}-team2`,
      label: match.team2_name,
      isWinner: match.results?.winner === match.team2_uuid,
      totalSetPoints: rightSetPoints,
      setPoints: team2SetPoints,
      opponentSetPoints: team1SetPoints,
      ballPoints: rightBallPoints,
      side: "right"
    }
  ];
}

function getCompetitionResultRows(match) {
  const team1SetPoints = getTeamSetPoints(match.matchState, "left");
  const team2SetPoints = getTeamSetPoints(match.matchState, "right");
  const totalSetPoints = getTotalSetPoints(match.matchState);
  const winnerSide = getWinnerSide(match.matchState);

  return [
    {
      key: `${match.id}-team1`,
      label: match.teamDescription1,
      isWinner: winnerSide === "team1",
      totalSetPoints: totalSetPoints.leftPoints,
      setPoints: team1SetPoints,
      opponentSetPoints: team2SetPoints,
      side: "left"
    },
    {
      key: `${match.id}-team2`,
      label: match.teamDescription2,
      isWinner: winnerSide === "team2",
      totalSetPoints: totalSetPoints.rightPoints,
      setPoints: team2SetPoints,
      opponentSetPoints: team1SetPoints,
      side: "right"
    }
  ];
}

function CompetitionMatchRow({ match, isMobile }) {
  const team1SetPoints = getTeamSetPoints(match.matchState, "left");
  const team2SetPoints = getTeamSetPoints(match.matchState, "right");
  const totalSetPoints = getTotalSetPoints(match.matchState);
  const winnerSide = getWinnerSide(match.matchState);
  const statusChip = getCompetitionStatusChip(match.matchState);
  const isFinished = Boolean(match.matchState?.finished);
  const isInProgress = match.matchState?.started && !match.matchState?.finished;
  const servingTeam = isInProgress ? match.matchState?.serving : null;

  if (isFinished) {
    return (
      <MatchResultCard
        dateLabel={formatMatchDate(match.date)}
        locationLabel={match.matchSeriesData?.name ?? "Unknown competition"}
        statusChip={statusChip}
        finished
        rows={getCompetitionResultRows(match)}
        compact={isMobile}
        showBallPoints={false}
      />
    );
  }

  return (
    <Box
      sx={{
        p: layout.padding.card,
        borderRadius: layout.radius.surface,
        bgcolor: "#ffffff",
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
          <StateChip
            label={statusChip.label}
            size="small"
            sx={statusChip.sx}
          />
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

function LeagueMatchRow({ match, isMobile }) {
  const statusChip = getLeagueStatusChip(match);
  const isFinished = Boolean(match.results?.winner);

  if (isFinished) {
    return (
      <MatchResultCard
        dateLabel={formatLeagueMatchDate(match.date, match.time)}
        locationLabel={match.location?.name ?? "Unknown location"}
        statusChip={statusChip}
        finished={match.finished}
        rows={getLeagueResultRows(match)}
        compact={isMobile}
        showBallPoints={!isMobile}
      />
    );
  }

  return (
    <Box
      sx={{
        p: layout.padding.card,
        borderRadius: layout.radius.surface,
        bgcolor: "#ffffff",
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
            {formatLeagueMatchDate(match.date, match.time)}
          </Typography>
          <StateChip
            label={statusChip.label}
            size="small"
            sx={statusChip.sx}
          />
        </Stack>
        <Typography sx={{ color: "rgba(26, 21, 18, 0.45)" }}>
          {match.location?.name ?? "Unknown location"}
        </Typography>
      </Stack>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 2fr) 32px",
          alignItems: "center",
          columnGap: 1.5
        }}
      >
        <Typography sx={{ fontWeight: match.results?.winner === match.team1_uuid ? 700 : 500 }}>
          {match.team1_name}
        </Typography>
        <Typography variant="body2" sx={{ textAlign: "center", fontWeight: 700 }}>
          -
        </Typography>
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 2fr) 32px",
          alignItems: "center",
          columnGap: 1.5
        }}
      >
        <Typography sx={{ fontWeight: match.results?.winner === match.team2_uuid ? 700 : 500 }}>
          {match.team2_name}
        </Typography>
        <Typography variant="body2" sx={{ textAlign: "center", fontWeight: 700 }}>
          -
        </Typography>
      </Box>
    </Box>
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

function getLeagueMatchesFromPlanPayload(data) {
  return (data.matchDays ?? [])
    .flatMap((matchDay) =>
      Object.values(matchDay.matches ?? {}).map((match) => ({
        ...match,
        matchDayName: matchDay.name,
        matchDayDate: matchDay.matchdate
      }))
    )
    .sort((left, right) => {
      const leftDateTime = `${left.date ?? ""}T${left.time ?? "00:00"}`;
      const rightDateTime = `${right.date ?? ""}T${right.time ?? "00:00"}`;

      return leftDateTime.localeCompare(rightDateTime);
    });
}

export default function EntityLive({ expectedEntityType }) {
  const location = useLocation();
  const { competitionUuid, leagueUuid } = useParams();
  const isMobile = useIsMobile();
  const [entityType, setEntityType] = useState(expectedEntityType ?? "competition");
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedTeamId, setSelectedTeamId] = useState("all");

  useEffect(() => {
    let isMounted = true;
    let isInitialLoad = true;

    async function loadMatches() {
      if (isInitialLoad) {
        setLoading(true);
        setError("");
      }

      try {
        if (expectedEntityType === "competition") {
          if (!competitionUuid) {
            throw new Error("Missing competition uuid");
          }

          const nextMatches = await fetchMatchesByCompetitionUuid(competitionUuid);

          if (isMounted) {
            setEntityType("competition");
            setMatches(nextMatches);
            setError("");
            setLoading(false);
          }
          return;
        }

        if (!leagueUuid) {
          throw new Error("Missing league uuid");
        }

        const data = await fetchJson("/api/plan");

        if (data.entityType !== "league") {
          throw new Error(`Unexpected entity type: ${data.entityType}`);
        }

        if (isMounted) {
          setEntityType("league");
          setMatches(getLeagueMatchesFromPlanPayload(data));
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
      expectedEntityType === "competition" ? 1000 : 20000
    );

    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
    };
  }, [competitionUuid, expectedEntityType, leagueUuid, location.pathname]);

  const teams = useMemo(() => {
    const teamMap = new Map();

    matches.forEach((match) => {
      if (entityType === "competition") {
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
        return;
      }

      if (match.team1_uuid && match.team1_name) {
        teamMap.set(match.team1_uuid, {
          id: match.team1_uuid,
          name: match.team1_name
        });
      }

      if (match.team2_uuid && match.team2_name) {
        teamMap.set(match.team2_uuid, {
          id: match.team2_uuid,
          name: match.team2_name
        });
      }
    });

    return Array.from(teamMap.values()).sort((left, right) => left.name.localeCompare(right.name));
  }, [entityType, matches]);

  const filterMatchesByTeam = (matchList) => {
    if (selectedTeamId === "all") {
      return matchList;
    }

    return matchList.filter((match) =>
      entityType === "competition"
        ? match.team1 === selectedTeamId || match.team2 === selectedTeamId
        : match.team1_uuid === selectedTeamId || match.team2_uuid === selectedTeamId
    );
  };

  const liveMatches = useMemo(() => {
    if (entityType === "competition") {
      return matches.filter((match) => match.matchState?.started && !match.matchState?.finished);
    }

    return [];
  }, [entityType, matches]);

  const upcomingMatches = useMemo(() => {
    if (entityType === "competition") {
      return matches.filter((match) => !match.matchState?.started);
    }

    const now = Date.now();
    return matches.filter((match) => {
      const timestamp = new Date(`${match.date ?? ""}${match.time ? `T${match.time}` : ""}`).getTime();
      return !match.results?.winner && !Number.isNaN(timestamp) && timestamp > now;
    });
  }, [entityType, matches]);

  const finishedMatches = useMemo(() => {
    if (entityType === "competition") {
      return matches.filter((match) => match.matchState?.finished);
    }

    return matches.filter((match) => Boolean(match.results?.winner));
  }, [entityType, matches]);

  const scheduledMatches = useMemo(() => {
    if (entityType !== "league") {
      return [];
    }

    const now = Date.now();
    return matches.filter((match) => {
      const timestamp = new Date(`${match.date ?? ""}${match.time ? `T${match.time}` : ""}`).getTime();
      return !match.results?.winner && (Number.isNaN(timestamp) || timestamp <= now);
    });
  }, [entityType, matches]);

  const filteredLiveMatches = filterMatchesByTeam(liveMatches);
  const filteredUpcomingMatches = filterMatchesByTeam(upcomingMatches);
  const filteredFinishedMatches = filterMatchesByTeam(finishedMatches);
  const filteredScheduledMatches = filterMatchesByTeam(scheduledMatches);

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
              {entityType === "league" && (
                <Typography color="text.secondary" textAlign="center">
                  League live uses the cached league schedule and results. The external live feed is
                  still competition-based.
                </Typography>
              )}
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

          {entityType === "competition" && (
            <MatchSection
              title="Live"
              matches={filteredLiveMatches}
              emptyText="No matches are currently in progress."
              renderMatch={(match) => <CompetitionMatchRow key={match.id} match={match} isMobile={isMobile} />}
            />
          )}

          {entityType === "league" && (
            <MatchSection
              title="Scheduled"
              matches={filteredScheduledMatches}
              emptyText="No scheduled matches found."
              renderMatch={(match) => <LeagueMatchRow key={match.uuid} match={match} isMobile={isMobile} />}
            />
          )}

          <MatchSection
            title="Upcoming Matches"
            matches={filteredUpcomingMatches}
            emptyText="No upcoming matches found."
            renderMatch={(match) =>
              entityType === "competition" ? (
                <CompetitionMatchRow key={match.id} match={match} isMobile={isMobile} />
              ) : (
                <LeagueMatchRow key={match.uuid} match={match} isMobile={isMobile} />
              )
            }
          />

          <MatchSection
            title="Finished Matches"
            matches={filteredFinishedMatches}
            emptyText="No finished matches found."
            renderMatch={(match) =>
              entityType === "competition" ? (
                <CompetitionMatchRow key={match.id} match={match} isMobile={isMobile} />
              ) : (
                <LeagueMatchRow key={match.uuid} match={match} isMobile={isMobile} />
              )
            }
          />
        </Box>
      )}
    </Box>
  );
}
