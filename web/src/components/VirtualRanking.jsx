import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow
} from "@mui/material";
import { getTeamShortName } from "../api/api.js";
import { buildRankingRowsFromMatches } from "./ranking.js";

export default function VirtualRanking({ matches, teamByUuid, compact = false }) {
  const rankingRows = buildRankingRowsFromMatches(matches, teamByUuid);
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
          <TableCell sx={{ ...cellSx, width: 34 }}>#</TableCell>
          <TableCell sx={cellSx}>Team</TableCell>
          <TableCell align="right" sx={{ ...cellSx, width: 48 }}>W/L</TableCell>
          <TableCell align="right" sx={{ ...cellSx, width: 56 }}>Sets</TableCell>
          <TableCell align="right" sx={{ ...cellSx, width: 42 }}>Diff</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {rankingRows.map((row) => (
          <TableRow key={row.teamUuid} hover>
            <TableCell sx={{ ...cellSx, width: 34 }}>{row.rank}</TableCell>
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
            <TableCell align="right" sx={{ ...cellSx, width: 48 }}>
              {row.wins}/{row.losses}
            </TableCell>
            <TableCell align="right" sx={{ ...cellSx, width: 56 }}>
              {row.setWins}:{row.setLosses}
            </TableCell>
            <TableCell align="right" sx={{ ...cellSx, width: 42 }}>
              {row.ballDifference}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
