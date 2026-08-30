import { useEffect, useState } from "react";
import { Alert, Box, Button, Card, CardContent, FormControl, InputLabel, List, ListItem, ListItemText, MenuItem, Select, Stack, Typography } from "@mui/material";
import { getApiData } from "../api.js";

const labels = { competition: { singular: "competition", plural: "Competitions" }, league: { singular: "league", plural: "Leagues" } };
const keyOf = (entry) => [entry.shortname, entry.name].filter(Boolean).join("\u0000") || entry.uuid;

export default function SelectionPage({ type, onFocus }) {
  const [seasons, setSeasons] = useState([]); const [associations, setAssociations] = useState([]); const [entries, setEntries] = useState([]);
  const [seasonId, setSeasonId] = useState(""); const [associationId, setAssociationId] = useState(""); const [entityKey, setEntityKey] = useState("");
  const [loading, setLoading] = useState(false); const [error, setError] = useState(""); const [ready, setReady] = useState(false);
  const entityLabels = labels[type]; const canLoad = Boolean(seasonId && associationId);
  useEffect(() => { let active = true; Promise.all([getApiData("/api/seasons", "season list"), getApiData("/api/associations", "association list")]).then(([s, a]) => { if (active) { setSeasons(s); setAssociations(a); } }).catch((e) => active && setError(e.message)).finally(() => active && setReady(true)); return () => { active = false; }; }, []);
  useEffect(() => { if (!canLoad) { setEntries([]); return undefined; } let active = true; setLoading(true); setError(""); const q = new URLSearchParams({ season_id: seasonId, association_id: associationId }); getApiData(`/api/${type}-list?${q}`, `${type} list`).then((data) => active && setEntries(data)).catch((e) => active && setError(e.message)).finally(() => active && setLoading(false)); return () => { active = false; }; }, [type, seasonId, associationId, canLoad]);
  const choices = entries.filter((entry, index) => entries.findIndex((candidate) => keyOf(candidate) === keyOf(entry)) === index);
  const results = entries.filter((entry) => keyOf(entry) === entityKey);
  const apply = (entry) => { const focus = { type, uuid: entry.uuid, name: entry.name || entry.shortname || entry.shortName || "Unnamed selection" }; window.localStorage.setItem("sams-score-board:focus", JSON.stringify(focus)); onFocus(focus); };
  return <Box component="main"><Stack spacing={1} mb={4}><Typography color="primary" fontWeight={700} variant="overline">Choose a focus</Typography><Typography variant="h4" component="h1">Select a {entityLabels.singular}</Typography><Typography color="text.secondary">Choose a season, association, and {entityLabels.singular}; then apply a matching entry.</Typography></Stack>
    <Card variant="outlined" sx={{ mb: 3 }}><CardContent><Stack spacing={2}>
      <FormControl fullWidth disabled={!ready || !seasons.length}><InputLabel>Season</InputLabel><Select label="Season" value={seasonId} onChange={(e) => { setSeasonId(e.target.value); setAssociationId(""); setEntityKey(""); }}>{seasons.map((s) => <MenuItem key={s.uuid} value={s.uuid}>{s.name || "Unnamed season"}</MenuItem>)}</Select></FormControl>
      <FormControl fullWidth disabled={!seasonId || !associations.length}><InputLabel>Association</InputLabel><Select label="Association" value={associationId} onChange={(e) => { setAssociationId(e.target.value); setEntityKey(""); }}>{associations.map((a) => <MenuItem key={a.uuid} value={a.uuid} sx={{ pl: 2 + (a.depth ?? 0) * 3 }}>{[a.shortname, a.name].filter(Boolean).join(" · ") || "Unnamed association"}</MenuItem>)}</Select></FormControl>
      <FormControl fullWidth disabled={!canLoad || loading}><InputLabel>{entityLabels.plural}</InputLabel><Select label={entityLabels.plural} value={entityKey} onChange={(e) => setEntityKey(e.target.value)}><MenuItem value=""><em>Select a {entityLabels.singular}</em></MenuItem>{choices.map((entry) => <MenuItem key={keyOf(entry)} value={keyOf(entry)}>{[entry.shortname, entry.name].filter(Boolean).join(" · ") || "Unnamed entry"}</MenuItem>)}</Select></FormControl>
    </Stack></CardContent></Card>
    {entityKey && !loading && !error && <Box><Typography variant="h6" mb={1}>Available entries</Typography><List disablePadding sx={{ border: 1, borderColor: "divider", borderRadius: 1 }}>{results.map((entry) => <ListItem key={entry.uuid} divider secondaryAction={<Button variant="contained" size="small" onClick={() => apply(entry)}>Apply</Button>}><ListItemText primary={entry.gender || "Unspecified"} secondary={[entry.shortname, entry.name].filter(Boolean).join(" · ")} /></ListItem>)}</List></Box>}
    {error && <Alert severity="info">{error}</Alert>}
  </Box>;
}
