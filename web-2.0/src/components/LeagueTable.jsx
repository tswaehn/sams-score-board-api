import { Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from "@mui/material";

export default function LeagueTable({ rankings }) {
  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small" aria-label="League standings">
        <TableHead>
          <TableRow>
            <TableCell>#</TableCell>
            <TableCell>Team</TableCell>
            <TableCell align="right">MP</TableCell>
            <TableCell align="right">W</TableCell>
            <TableCell align="right">L</TableCell>
            <TableCell align="right">Sets</TableCell>
            <TableCell align="right">Pts</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rankings.map((ranking) => (
            <TableRow key={ranking.uuid}>
              <TableCell>{ranking.rank ?? "–"}</TableCell>
              <TableCell>{ranking.teamName || "Unnamed team"}</TableCell>
              <TableCell align="right">{ranking.matchesPlayed ?? "–"}</TableCell>
              <TableCell align="right">{ranking.wins ?? "–"}</TableCell>
              <TableCell align="right">{ranking.losses ?? "–"}</TableCell>
              <TableCell align="right">{ranking.setWins ?? "–"}:{ranking.setLosses ?? "–"}</TableCell>
              <TableCell align="right">{ranking.points ?? "–"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
