import { Box, Button, FormControl, InputLabel, MenuItem, Select, Stack, Typography } from "@mui/material";

function formatDate(value) {
  if (!value) return "Date not set";
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("de-DE", { dateStyle: "medium" }).format(date);
}

function label(matchDay) {
  return matchDay.name || "Match day";
}

export default function LeagueMatchDays({ matchDays, selectedUuid, onSelect }) {
  const selectedMatchDay = matchDays.find((matchDay) => matchDay.uuid === selectedUuid);

  return <Stack spacing={1.5}>
    <FormControl fullWidth sx={{ display: { xs: "block", sm: "none" } }}>
      <InputLabel id="match-day-label">Match day</InputLabel>
      <Select labelId="match-day-label" label="Match day" value={selectedUuid} onChange={(event) => onSelect(event.target.value)}>
        {matchDays.map((matchDay) => <MenuItem key={matchDay.uuid} value={matchDay.uuid}>{label(matchDay)} · {formatDate(matchDay.matchdate || matchDay.matchDate)}</MenuItem>)}
      </Select>
    </FormControl>
    <Box sx={{ display: { xs: "none", sm: "flex" }, flexWrap: "wrap", gap: 1 }}>
      {matchDays.map((matchDay) => <Button key={matchDay.uuid} variant={matchDay.uuid === selectedUuid ? "contained" : "outlined"} onClick={() => onSelect(matchDay.uuid)}>
        {label(matchDay)}
      </Button>)}
    </Box>
    {selectedMatchDay && <Typography variant="body2" color="text.secondary">{formatDate(selectedMatchDay.matchdate || selectedMatchDay.matchDate)}</Typography>}
  </Stack>;
}
