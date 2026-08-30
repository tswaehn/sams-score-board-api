import { useEffect, useState } from "react";
import { Alert, Avatar, Box, List, ListItem, ListItemText, Typography } from "@mui/material";
import { getApiData } from "../api.js";

export default function TeamsPage({ focus }) {
  const [teams, setTeams] = useState([]); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  useEffect(() => { if (!focus) return undefined; let active = true; setLoading(true); getApiData(`/api/${focus.type}/${focus.uuid}/teams`, "teams").then((data) => active && setTeams(data)).catch((e) => active && setError(e.message)).finally(() => active && setLoading(false)); return () => { active = false; }; }, [focus]);
  if (!focus) return <Alert severity="info">Choose a competition or league before opening its teams.</Alert>;
  return <Box component="main"><Typography variant="h4" component="h1" mb={4}>Teams</Typography>{loading && <Typography color="text.secondary">Loading teams…</Typography>}{error && <Alert severity="error">{error}</Alert>}{!loading && !error && teams.length === 0 && <Alert severity="info">No teams are available for this {focus.type}.</Alert>}{!loading && !error && teams.length > 0 && <List disablePadding sx={{ border: 1, borderColor: "divider", borderRadius: 1 }}>{teams.map((team) => <ListItem key={team.uuid} divider>{team.logoImageForScreenOutputLink || team.logoImageLink ? <Box component="img" src={team.logoImageForScreenOutputLink || team.logoImageLink} alt={team.name || "Team"} sx={{ width: 40, height: 40, mr: 2, objectFit: "contain" }} /> : <Avatar sx={{ mr: 2 }}>{(team.name || "?").slice(0, 1)}</Avatar>}<ListItemText primary={team.name || team.shortName || "Unnamed team"} secondary={team.shortName || undefined} /></ListItem>)}</List>}</Box>;
}
