import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow
} from "@mui/material";
import { getTeamShortName } from "../api/api.js";

function parseScorePair(value) {
  const [leftRaw = "0", rightRaw = "0"] = `${value ?? ""}`.split(":");
  const left = Number.parseInt(leftRaw, 10);
  const right = Number.parseInt(rightRaw, 10);

  return {
    left: Number.isNaN(left) ? 0 : left,
    right: Number.isNaN(right) ? 0 : right
  };
}

function createEmptyStats(teamUuid, teamName) {
  return {
    teamUuid,
    teamName,
    wins: 0,
    losses: 0,
    setWins: 0,
    setLosses: 0,
    ballWins: 0,
    ballLosses: 0
  };
}

function getOrCreateTeamStats(statsByTeam, teamUuid, teamName) {
  if (!statsByTeam.has(teamUuid)) {
    statsByTeam.set(teamUuid, createEmptyStats(teamUuid, teamName));
  }

  return statsByTeam.get(teamUuid);
}

function buildVirtualRankingRows(matches, teamByUuid) {
  const statsByTeam = new Map();
  const finishedMatches = matches.filter((match) =>
    Boolean(match?.finished || match?.results?.winner)
  );

  finishedMatches.forEach((match) => {
    const team1Name = teamByUuid.get(match.team1_uuid)?.name ?? match.team1_name ?? match.team1_uuid ?? "";
    const team2Name = teamByUuid.get(match.team2_uuid)?.name ?? match.team2_name ?? match.team2_uuid ?? "";
    const team1Stats = getOrCreateTeamStats(statsByTeam, match.team1_uuid, team1Name);
    const team2Stats = getOrCreateTeamStats(statsByTeam, match.team2_uuid, team2Name);
    const setPoints = parseScorePair(match?.results?.setPoints);
    const ballPoints = parseScorePair(match?.results?.ballPoints);

    team1Stats.setWins += setPoints.left;
    team1Stats.setLosses += setPoints.right;
    team2Stats.setWins += setPoints.right;
    team2Stats.setLosses += setPoints.left;

    team1Stats.ballWins += ballPoints.left;
    team1Stats.ballLosses += ballPoints.right;
    team2Stats.ballWins += ballPoints.right;
    team2Stats.ballLosses += ballPoints.left;

    if (match?.results?.winner === match.team1_uuid || setPoints.left > setPoints.right) {
      team1Stats.wins += 1;
      team2Stats.losses += 1;
    } else if (match?.results?.winner === match.team2_uuid || setPoints.right > setPoints.left) {
      team2Stats.wins += 1;
      team1Stats.losses += 1;
    }
  });

  return Array.from(statsByTeam.values())
    .sort((left, right) => {
      if (right.setWins !== left.setWins) {
        return right.setWins - left.setWins;
      }

      const leftSetDiff = left.setWins - left.setLosses;
      const rightSetDiff = right.setWins - right.setLosses;

      if (rightSetDiff !== leftSetDiff) {
        return rightSetDiff - leftSetDiff;
      }

      const leftBallDiff = left.ballWins - left.ballLosses;
      const rightBallDiff = right.ballWins - right.ballLosses;

      if (rightBallDiff !== leftBallDiff) {
        return rightBallDiff - leftBallDiff;
      }

      if (right.wins !== left.wins) {
        return right.wins - left.wins;
      }

      return left.teamName.localeCompare(right.teamName);
    })
    .map((row, index) => ({
      rank: index + 1,
      ...row,
      ballDifference: row.ballWins - row.ballLosses
    }));
}

export default function VirtualRanking({ matches, teamByUuid, compact = false }) {
  const rankingRows = buildVirtualRankingRows(matches, teamByUuid);
  const cellSx = { px: 1, py: 0.4, fontSize: "0.8rem", lineHeight: 1.2 };

  if (rankingRows.length === 0) {
    return null;
  }

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
        {rankingRows.map((row) => (
          <TableRow key={row.teamUuid} hover>
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
                ? getTeamShortName(row.teamName, teamByUuid.get(row.teamUuid)?.short_name, 16)
                : row.teamName}
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
        ))}
      </TableBody>
    </Table>
  );
}
