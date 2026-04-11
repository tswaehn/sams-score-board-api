import {
  Box,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography
} from "@mui/material";
import { getTeamShortName } from "../api/api.js";
import { layout } from "./layout.js";
import FullScreenMatch from "./FullScreenMatch.jsx";
import VirtualRanking from "./VirtualRanking.jsx";
import {
  getPlannedMatchStatusChip,
  getPlannedGroupStatusChip,
  StatusChip
} from "./stateChip.jsx";

function getSetBallPoints(match, side) {
  const sets = match?.results?.sets ?? [];

  return sets.map((set) => {
    const [leftPoints = "-", rightPoints = "-"] = (set.ballPoints ?? "").split(":");
    return side === "left" ? leftPoints : rightPoints;
  });
}

function getMatchBallPoints(match) {
  const [leftPoints = "-", rightPoints = "-"] = (match?.results?.ballPoints ?? "").split(":");
  return { leftPoints, rightPoints };
}

function getMatchSetPoints(match) {
  const [leftPoints = "-", rightPoints = "-"] = (match?.results?.setPoints ?? "").split(":");
  return { leftPoints, rightPoints };
}

function getMatchResultRows(match, teamByUuid) {
  const team1 = teamByUuid.get(match.team1_uuid);
  const team2 = teamByUuid.get(match.team2_uuid);
  const team1SetPoints = getSetBallPoints(match, "left");
  const team2SetPoints = getSetBallPoints(match, "right");
  const totalBallPoints = getMatchBallPoints(match);
  const totalSetPoints = getMatchSetPoints(match);
  const winnerUuid = match.results?.winner;

  return [
    {
      key: `${match.uuid}-team1`,
      teamName: team1?.name ?? match.team1_name ?? match.team1_uuid ?? "",
      teamShortName: team1?.short_name,
      isWinner: winnerUuid === match.team1_uuid,
      totalSetPoints: totalSetPoints.leftPoints,
      setPoints: team1SetPoints,
      opponentSetPoints: team2SetPoints,
      ballPoints: totalBallPoints.leftPoints,
      side: "left"
    },
    {
      key: `${match.uuid}-team2`,
      teamName: team2?.name ?? match.team2_name ?? match.team2_uuid ?? "",
      teamShortName: team2?.short_name,
      isWinner: winnerUuid === match.team2_uuid,
      totalSetPoints: totalSetPoints.rightPoints,
      setPoints: team2SetPoints,
      opponentSetPoints: team1SetPoints,
      ballPoints: totalBallPoints.rightPoints,
      side: "right"
    }
  ];
}

function FullScreenRankingHeader({ group }) {
  return (
    <Stack
      direction="row"
      spacing={1}
      justifyContent="space-between"
      alignItems="center"
    >
      <Stack spacing={0.25} sx={{ minWidth: 0 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.1 }}>
          {group.name}
        </Typography>
      </Stack>
      <StatusChip type={getPlannedGroupStatusChip(group)} size="xsmall" />
    </Stack>
  );
}

function FullScreenRankingTableBody({ group, rankingRows, teamByName, compact }) {
  const cellSx = { px: 1, py: 0.4, fontSize: "0.8rem", lineHeight: 1.2 };

  return (
    <Table
      size="small"
      sx={{
        tableLayout: "fixed",
        width: "100%"
      }}
    >
      <TableHead>
        <TableRow>
          <TableCell sx={{ ...cellSx, width: 44 }}>Rank</TableCell>
          <TableCell sx={cellSx}>Team</TableCell>
          <TableCell align="right" sx={{ ...cellSx, width: 60 }}>W/L</TableCell>
          <TableCell align="right" sx={{ ...cellSx, width: 72 }}>Sets</TableCell>
          <TableCell align="right" sx={{ ...cellSx, width: 52 }}>Diff</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {rankingRows.map((row) => {
          const team = teamByName.get(row.teamName);
          const teamName = team?.name ?? row.teamName;

          return (
            <TableRow key={`${group.uuid}-${row.rank}`} hover>
              <TableCell sx={{ ...cellSx, width: 44 }}>{row.rank}</TableCell>
              <TableCell
                sx={{
                  ...cellSx,
                  fontWeight: 600,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis"
                }}
              >
                {compact
                  ? getTeamShortName(teamName, team?.short_name, 16)
                  : teamName}
              </TableCell>
              <TableCell align="right" sx={{ ...cellSx, width: 60 }}>
                {row.wins}/{row.losses}
              </TableCell>
              <TableCell align="right" sx={{ ...cellSx, width: 72 }}>
                {row.setWins}:{row.setLosses}
              </TableCell>
              <TableCell align="right" sx={{ ...cellSx, width: 52 }}>
                {row.ballDifference}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

function FullScreenRankingMatchesBody({ matches, teamByUuid, compact }) {
  if (matches.length === 0) {
    return (
      <Typography color="text.secondary">
        No ranking or match data available for this stage.
      </Typography>
    );
  }

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
        gap: layout.gap.cardList
      }}
    >
      {matches.map((match) => (
        <FullScreenMatch
          key={match.uuid}
          dateLabel={[
            match.date,
            match.time,
            match.matchNumber != null ? `(Spiel ${match.matchNumber})` : null
          ].filter(Boolean).join(" · ")}
          statusChip={getPlannedMatchStatusChip(match)}
          rows={getMatchResultRows(match, teamByUuid)}
        />
      ))}
    </Box>
  );
}

export default function FullScreenRanking({
  group,
  rankingRows,
  matches,
  teamByName,
  teamByUuid,
  compact = false
}) {
  return (
    <Paper
      elevation={0}
      sx={{
        minWidth: 0,
        height: "100%",
        p: 1,
        borderRadius: 0.5,
        border: "1px solid rgba(20, 17, 15, 0.08)",
        bgcolor: "background.paper",
        display: "grid",
        gap: 0.5
      }}
    >
      <FullScreenRankingHeader group={group} />

      {rankingRows.length > 0 ? (
        <FullScreenRankingTableBody
          group={group}
          rankingRows={rankingRows}
          teamByName={teamByName}
          compact={compact}
        />
      ) : (
        <VirtualRanking
          matches={matches}
          teamByUuid={teamByUuid}
          compact={compact}
        />
      )}

      {!group?.finished && (
        <Box sx={{ pt: 0.25 }}>
          <FullScreenRankingMatchesBody
            matches={matches}
            teamByUuid={teamByUuid}
            compact={compact}
          />
        </Box>
      )}
    </Paper>
  );
}
