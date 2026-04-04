import { useEffect, useMemo, useState } from "react";
import {
  Avatar,
  Box,
  FormControl,
  InputLabel,
  Paper,
  MenuItem,
  Select,
  Stack,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography
} from "@mui/material";
import { useLocation } from "react-router-dom";
import {
  fetchJson,
  getTeamShortName,
  useIsMobile
} from "../api/api.js";
import { layout } from "../components/layout.js";

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

function getSetBallPoints(match, side) {
  const sets = match?.results?.sets ?? [];

  return sets.map((set) => {
    const [leftPoints = "-", rightPoints = "-"] = (set.ballPoints ?? "").split(":");
    return side === "left" ? leftPoints : rightPoints;
  });
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

function getMatchBallPoints(match) {
  const [leftPoints = "-", rightPoints = "-"] = (match?.results?.ballPoints ?? "").split(":");
  return { leftPoints, rightPoints };
}

function getMatchSetPoints(match) {
  const [leftPoints = "-", rightPoints = "-"] = (match?.results?.setPoints ?? "").split(":");
  return { leftPoints, rightPoints };
}

function GroupDropdown({ activeGroupId, groups, label, onChange }) {
  return (
    <Box sx={{ display: "flex", justifyContent: "center" }}>
      <FormControl size="small" sx={{ minWidth: 220, maxWidth: 360 }}>
        <InputLabel id="plan-group-label">{label}</InputLabel>
        <Select
          labelId="plan-group-label"
          value={activeGroupId ?? ""}
          label={label}
          onChange={(event) => onChange(event.target.value)}
        >
          {groups.map((group) => (
            <MenuItem key={group.uuid} value={group.uuid}>
              {group.name}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </Box>
  );
}

function GroupTabs({ activeGroupId, groups, onChange }) {
  return (
    <Tabs
      value={activeGroupId}
      onChange={(_, value) => onChange(value)}
      variant="scrollable"
      allowScrollButtonsMobile
      textColor="inherit"
      indicatorColor="secondary"
    >
      {groups.map((group) => (
        <Tab key={group.uuid} value={group.uuid} label={group.name} />
      ))}
    </Tabs>
  );
}

function RankingTable({ activeGroup, rankingRows, teamByName }) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: layout.padding.surface,
        borderRadius: layout.radius.surface,
        border: "1px solid rgba(20, 17, 15, 0.08)",
        bgcolor: "teamInfo.main"
      }}
    >
      <Table size="small">
        <TableHead sx={{ bgcolor: "teamInfo.main" }}>
          <TableRow>
            <TableCell>Rank</TableCell>
            <TableCell>Team</TableCell>
            <TableCell align="right">Matches</TableCell>
            <TableCell align="right">W/L</TableCell>
            <TableCell align="right">Sets</TableCell>
            <TableCell align="right">Balls</TableCell>
            <TableCell align="right">Diff</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rankingRows.map((row) => {
            const team = teamByName.get(row.teamName);

            return (
              <TableRow key={`${activeGroup.uuid}-${row.rank}`} hover>
                <TableCell>{row.rank}</TableCell>
                <TableCell>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <Avatar
                      src={team?.logo_url}
                      alt={`${row.teamName} logo`}
                      sx={{ width: 36, height: 36, bgcolor: "#f3ebe0" }}
                    />
                    <Typography sx={{ fontWeight: 600 }}>
                      {team?.name ?? row.teamName}
                    </Typography>
                  </Stack>
                </TableCell>
                <TableCell align="right">{row.matchesPlayed}</TableCell>
                <TableCell align="right">
                  {row.wins}/{row.losses}
                </TableCell>
                <TableCell align="right">
                  {row.setWins}:{row.setLosses}
                </TableCell>
                <TableCell align="right">
                  {row.ballWins}:{row.ballLosses}
                </TableCell>
                <TableCell align="right">{row.ballDifference}</TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </Paper>
  );
}

function MobileRankingTable({ activeGroup, rankingRows, teamByName }) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: layout.padding.surface,
        borderRadius: layout.radius.surface,
        border: "1px solid rgba(20, 17, 15, 0.08)",
        bgcolor: "teamInfo.main"
      }}
    >
      <Table size="small">
        <TableHead sx={{ bgcolor: "teamInfo.main" }}>
          <TableRow>
            <TableCell>Team</TableCell>
            <TableCell align="right">W/L</TableCell>
            <TableCell align="right">Sets</TableCell>
            <TableCell align="right">Balls</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rankingRows.map((row) => {
            const team = teamByName.get(row.teamName);

            return (
              <TableRow key={`${activeGroup.uuid}-${row.rank}`} hover>
                <TableCell>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <Avatar
                      src={team?.logo_url}
                      alt={`${row.teamName} logo`}
                      sx={{ width: 36, height: 36, bgcolor: "#f3ebe0" }}
                    />
                    <Typography sx={{ fontWeight: 600 }}>
                      {getTeamShortName(team?.name ?? row.teamName, team?.short_name, 7)}
                    </Typography>
                  </Stack>
                </TableCell>
                <TableCell align="right">
                  {row.wins}/{row.losses}
                </TableCell>
                <TableCell align="right">
                  {row.setWins}:{row.setLosses}
                </TableCell>
                <TableCell align="right">
                  {row.ballWins}:{row.ballLosses}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </Paper>
  );
}

function MatchCard({ match, teamByUuid }) {
  const team1 = teamByUuid.get(match.team1_uuid);
  const team2 = teamByUuid.get(match.team2_uuid);
  const team1Label = team1?.name ?? match.team1_name ?? match.team1_uuid ?? "";
  const team2Label = team2?.name ?? match.team2_name ?? match.team2_uuid ?? "";
  const team1SetPoints = getSetBallPoints(match, "left");
  const team2SetPoints = getSetBallPoints(match, "right");
  const totalBallPoints = getMatchBallPoints(match);
  const totalSetPoints = getMatchSetPoints(match);
  const winnerUuid = match.results?.winner;

  return (
    <Box
      sx={{
        p: layout.padding.surface,
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
        <Typography sx={{ fontWeight: 600, color: "rgba(26, 21, 18, 0.45)" }}>
          {match.date}
          {match.time ? ` · ${match.time}` : ""}
          {match.matchNumber != null ? `  (Spiel ${match.matchNumber})` : ""}
        </Typography>
        <Typography sx={{ color: "rgba(26, 21, 18, 0.45)" }}>
          {match.location?.name}
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
        <Typography sx={{ fontWeight: winnerUuid === match.team1_uuid ? 700 : 500 }}>
          {team1Label}
        </Typography>
        <Typography
          variant="body2"
          sx={{
            width: 32,
            textAlign: "center",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 700
          }}
        >
          {totalSetPoints.leftPoints}
        </Typography>
        <Stack direction="row" spacing={1} justifyContent="flex-end" sx={{ justifySelf: "end" }}>
          {team1SetPoints.map((points, index) => {
            const opposingPoints = team2SetPoints[index] ?? "-";

            return (
              <Typography
                key={`${match.uuid}-team1-set-${index + 1}`}
                variant="body2"
                color="text.secondary"
                sx={{
                  width: 32,
                  textAlign: "center",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  ...getSetPointStyles(points, opposingPoints, "left")
                }}
              >
                {points}
              </Typography>
            );
          })}
          <Typography
            variant="body2"
            sx={{
              width: 40,
              textAlign: "center",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              color: "rgba(26, 21, 18, 0.45)"
            }}
          >
            {totalBallPoints.leftPoints}
          </Typography>
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
        <Typography sx={{ fontWeight: winnerUuid === match.team2_uuid ? 700 : 500 }}>
          {team2Label}
        </Typography>
        <Typography
          variant="body2"
          sx={{
            width: 32,
            textAlign: "center",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 700
          }}
        >
          {totalSetPoints.rightPoints}
        </Typography>
        <Stack direction="row" spacing={1} justifyContent="flex-end" sx={{ justifySelf: "end" }}>
          {team2SetPoints.map((points, index) => {
            const opposingPoints = team1SetPoints[index] ?? "-";

            return (
              <Typography
                key={`${match.uuid}-team2-set-${index + 1}`}
                variant="body2"
                color="text.secondary"
                sx={{
                  width: 32,
                  textAlign: "center",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  ...getSetPointStyles(opposingPoints, points, "right")
                }}
              >
                {points}
              </Typography>
            );
          })}
          <Typography
            variant="body2"
            sx={{
              width: 40,
              textAlign: "center",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              color: "rgba(26, 21, 18, 0.45)"
            }}
          >
            {totalBallPoints.rightPoints}
          </Typography>
        </Stack>
      </Box>
    </Box>
  );
}

function MobileMatchCard({ match, teamByUuid }) {
  const team1 = teamByUuid.get(match.team1_uuid);
  const team2 = teamByUuid.get(match.team2_uuid);
  const team1Label = getTeamShortName(
    team1?.name ?? match.team1_name ?? match.team1_uuid ?? "",
    team1?.short_name
  );
  const team2Label = getTeamShortName(
    team2?.name ?? match.team2_name ?? match.team2_uuid ?? "",
    team2?.short_name
  );
  const team1SetPoints = getSetBallPoints(match, "left");
  const team2SetPoints = getSetBallPoints(match, "right");
  const totalSetPoints = getMatchSetPoints(match);
  const winnerUuid = match.results?.winner;

  return (
    <Box
      sx={{
        p: layout.padding.surface,
        borderRadius: layout.radius.surface,
        bgcolor: "background.paper",
        display: "grid",
        gap: layout.gap.surface
      }}
    >
      <Typography sx={{ fontWeight: 600, color: "rgba(26, 21, 18, 0.45)" }}>
        {match.date}
        {match.time ? ` · ${match.time}` : ""}
        {match.matchNumber != null ? `  (Spiel ${match.matchNumber})` : ""}
      </Typography>
      <Typography sx={{ color: "rgba(26, 21, 18, 0.45)" }}>
        {match.location?.name}
      </Typography>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1fr) 32px minmax(0, 1fr)",
          alignItems: "center",
          columnGap: 1
        }}
      >
        <Typography sx={{ fontWeight: winnerUuid === match.team1_uuid ? 700 : 500 }}>
          {team1Label}
        </Typography>
        <Typography
          variant="body2"
          sx={{
            width: 32,
            textAlign: "center",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 700
          }}
        >
          {totalSetPoints.leftPoints}
        </Typography>
        <Stack direction="row" spacing={0.5} justifyContent="flex-end" sx={{ justifySelf: "end" }}>
          {team1SetPoints.map((points, index) => {
            const opposingPoints = team2SetPoints[index] ?? "-";

            return (
              <Typography
                key={`${match.uuid}-mobile-team1-set-${index + 1}`}
                variant="body2"
                color="text.secondary"
                sx={{
                  width: 28,
                  textAlign: "center",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  ...getSetPointStyles(points, opposingPoints, "left")
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
          gridTemplateColumns: "minmax(0, 1fr) 32px minmax(0, 1fr)",
          alignItems: "center",
          columnGap: 1
        }}
      >
        <Typography sx={{ fontWeight: winnerUuid === match.team2_uuid ? 700 : 500 }}>
          {team2Label}
        </Typography>
        <Typography
          variant="body2"
          sx={{
            width: 32,
            textAlign: "center",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 700
          }}
        >
          {totalSetPoints.rightPoints}
        </Typography>
        <Stack direction="row" spacing={0.5} justifyContent="flex-end" sx={{ justifySelf: "end" }}>
          {team2SetPoints.map((points, index) => {
            const opposingPoints = team1SetPoints[index] ?? "-";

            return (
              <Typography
                key={`${match.uuid}-mobile-team2-set-${index + 1}`}
                variant="body2"
                color="text.secondary"
                sx={{
                  width: 28,
                  textAlign: "center",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  ...getSetPointStyles(opposingPoints, points, "right")
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

export default function EntityPlan({ expectedEntityType }) {
  const location = useLocation();
  const isMobile = useIsMobile();
  const [entityType, setEntityType] = useState(expectedEntityType ?? "competition");
  const [entity, setEntity] = useState(null);
  const [association, setAssociation] = useState(null);
  const [season, setSeason] = useState(null);
  const [matchGroups, setMatchGroups] = useState([]);
  const [matchDays, setMatchDays] = useState([]);
  const [rankings, setRankings] = useState({});
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeGroupId, setActiveGroupId] = useState(null);
  const [selectedTeamUuid, setSelectedTeamUuid] = useState("all");

  useEffect(() => {
    let isMounted = true;
    let isInitialLoad = true;

    async function loadPlan() {
      if (isInitialLoad) {
        setLoading(true);
        setError("");
      }

      try {
        const data = await fetchJson("/api/plan");

        if (isMounted) {
          const nextEntityType = data.entityType ?? expectedEntityType ?? "competition";

          if (expectedEntityType && nextEntityType !== expectedEntityType) {
            setError(`Unexpected entity type: ${nextEntityType}`);
            setLoading(false);
            return;
          }

          const nextGroups =
            nextEntityType === "league" ? data.matchDays ?? [] : data.matchGroups ?? [];
          setEntityType(nextEntityType);
          setEntity(data.entity);
          setAssociation(data.association);
          setSeason(data.season);
          setMatchGroups(data.matchGroups ?? []);
          setMatchDays(data.matchDays ?? []);
          setRankings(data.rankings);
          setTeams(data.teams);
          setActiveGroupId((current) =>
            nextGroups.some((group) => group.uuid === current)
              ? current
              : nextGroups[0]?.uuid ?? null
          );
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

    loadPlan();
    const intervalId = window.setInterval(loadPlan, 20000);

    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
    };
  }, [expectedEntityType, location.pathname]);

  const groups = entityType === "league" ? matchDays : matchGroups;

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

  const activeGroup = groups.find((group) => group.uuid === activeGroupId) ?? null;
  const rankingKey =
    entityType === "league" ? Object.keys(rankings)[0] ?? "" : activeGroup?.name ?? "";
  const rankingRows = rankingKey ? getRankingRows(rankings, rankingKey) : [];
  const matchRows = activeGroup ? getSortedMatches(activeGroup) : [];
  const filteredMatchRows = matchRows.filter((match) => {
    if (selectedTeamUuid === "all") {
      return true;
    }

    return match.team1_uuid === selectedTeamUuid || match.team2_uuid === selectedTeamUuid;
  });

  const selectableTeams = useMemo(() => {
    const uuids = new Set();

    matchRows.forEach((match) => {
      if (match.team1_uuid) {
        uuids.add(match.team1_uuid);
      }

      if (match.team2_uuid) {
        uuids.add(match.team2_uuid);
      }
    });

    return Array.from(uuids)
      .map((teamUuid) => teamByUuid.get(teamUuid))
      .filter(Boolean)
      .sort((left, right) => left.name.localeCompare(right.name));
  }, [matchRows, teamByUuid]);

  useEffect(() => {
    setSelectedTeamUuid("all");
  }, [activeGroupId]);

  return (
    <Box sx={{ display: "grid", gap: layout.gap.page }}>
      {loading && <Typography color="text.secondary">Loading plan...</Typography>}
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
              bgcolor: "background.paper"
            }}
          >
            <Typography variant="h5" sx={{ fontWeight: 700 }}>
              {entity?.name}
            </Typography>
            <Typography color="text.secondary">
              {association?.name} · {season?.name}
            </Typography>
          </Paper>

          {groups.length > 0 && (
            isMobile ? (
              <GroupDropdown
                activeGroupId={activeGroupId}
                groups={groups}
                label={entityType === "league" ? "Match day" : "Match group"}
                onChange={setActiveGroupId}
              />
            ) : (
              <GroupTabs
                activeGroupId={activeGroupId}
                groups={groups}
                onChange={setActiveGroupId}
              />
            )
          )}

          {activeGroup && (
            <Paper
              elevation={0}
              sx={{
                p: layout.padding.section,
                borderRadius: layout.radius.surface,
                border: "1px solid rgba(20, 17, 15, 0.08)",
                bgcolor: "background.paper",
                display: "grid",
                gap: layout.gap.section
              }}
            >
              <Box>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  {activeGroup.name}
                </Typography>
                <Typography color="text.secondary">
                  {entityType === "league"
                    ? activeGroup.matchdate?.split("T", 1)[0] ?? ""
                    : `Tourney level ${activeGroup.tourneyLevel}`}
                </Typography>
              </Box>

              {isMobile ? (
                <MobileRankingTable
                  activeGroup={activeGroup}
                  rankingRows={rankingRows}
                  teamByName={teamByName}
                />
              ) : (
                <RankingTable
                  activeGroup={activeGroup}
                  rankingRows={rankingRows}
                  teamByName={teamByName}
                />
              )}

              <Paper
                elevation={0}
                sx={{
                  p: layout.padding.surface,
                  borderRadius: layout.radius.surface,
                  border: "1px solid rgba(20, 17, 15, 0.08)",
                  bgcolor: "teamInfo.main",
                  display: "grid",
                  gap: layout.gap.surface
                }}
              >
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                  Matches
                </Typography>

                <FormControl size="small" sx={{ minWidth: 220, maxWidth: 320 }}>
                  <InputLabel id="plan-team-filter-label">Team</InputLabel>
                  <Select
                    labelId="plan-team-filter-label"
                    value={selectedTeamUuid}
                    label="Team"
                    onChange={(event) => setSelectedTeamUuid(event.target.value)}
                  >
                    <MenuItem value="all">All teams</MenuItem>
                    {selectableTeams.map((team) => (
                      <MenuItem key={team.uuid} value={team.uuid}>
                        {team.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                {matchRows.length === 0 && (
                  <Typography color="text.secondary">
                    No matches available for this section.
                  </Typography>
                )}

                {matchRows.length > 0 && filteredMatchRows.length === 0 && (
                  <Typography color="text.secondary">
                    No matches found for the selected team.
                  </Typography>
                )}

                {filteredMatchRows.map((match) =>
                  isMobile ? (
                    <MobileMatchCard key={match.uuid} match={match} teamByUuid={teamByUuid} />
                  ) : (
                    <MatchCard key={match.uuid} match={match} teamByUuid={teamByUuid} />
                  )
                )}
              </Paper>
            </Paper>
          )}
        </Box>
      )}
    </Box>
  );
}

