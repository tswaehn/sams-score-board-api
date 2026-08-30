import { List, ListItem, ListItemText, Paper } from "@mui/material";

function teamName(match, number) {
  return match[`team${number}Description`] || match._embedded?.[`team${number}`]?.name || `Team ${number}`;
}

function score(match) {
  if (typeof match.results === "string") return match.results;
  if (Array.isArray(match.results)) return match.results.map((result) => result.result || result).join(" · ");
  return "–";
}

export default function LeagueMatches({ matches }) {
  return <List component={Paper} variant="outlined" disablePadding aria-label="Matches">
    {matches.map((match) => <ListItem key={match.uuid} divider>
      <ListItemText primary={`${teamName(match, 1)} – ${teamName(match, 2)}`} secondary={`${match.time || "Time not set"} · ${score(match)}`} />
    </ListItem>)}
  </List>;
}
