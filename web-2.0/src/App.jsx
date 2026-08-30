import { useEffect, useState } from "react";
import MenuIcon from "@mui/icons-material/Menu";
import SportsVolleyballIcon from "@mui/icons-material/SportsVolleyball";
import { Alert, AppBar, Box, Button, Card, CardContent, Chip, Container, FormControl, InputLabel, List, ListItem, ListItemText, Menu, MenuItem, Select, Stack, Toolbar, Typography } from "@mui/material";
import "./App.css";

const labels = { competition: { singular: "competition", plural: "Competitions" }, league: { singular: "league", plural: "Leagues" } };
const apiUrl = (window.SAMS_SCORE_BOARD_CONFIG?.apiUrl || "").replace(/\/$/, "");
const apiPath = (path) => `${apiUrl}${path}`;

function readFocus() {
  try {
    const saved = JSON.parse(window.localStorage.getItem("sams-score-board:focus"));
    return saved?.type && saved?.uuid ? saved : null;
  } catch { return null; }
}

function entityKey(entry) {
  return [entry.shortname, entry.name].filter(Boolean).join("\u0000");
}

function SelectorPage({ type, onFocus }) {
  const [entries, setEntries] = useState([]);
  const [seasons, setSeasons] = useState([]);
  const [seasonId, setSeasonId] = useState("");
  const [associations, setAssociations] = useState([]);
  const [associationId, setAssociationId] = useState("");
  const [selectedEntityKey, setSelectedEntityKey] = useState("");
  const [loading, setLoading] = useState(true);
  const [seasonLoading, setSeasonLoading] = useState(true);
  const [error, setError] = useState("");
  const typeLabels = labels[type];
  const canLoadEntries = Boolean(seasonId && associationId);

  useEffect(() => {
    let active = true;
    fetch(apiPath("/api/seasons"))
      .then(async (response) => {
        if (!response.ok) throw new Error("The season list could not be loaded.");
        const payload = await response.json();
        return Array.isArray(payload) ? payload : payload.data ?? [];
      })
      .then((data) => {
        if (!active) return;
        setSeasons(data);
      })
      .catch((reason) => active && setError(reason.message))
      .finally(() => active && setSeasonLoading(false));
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    fetch(apiPath("/api/associations"))
      .then(async (response) => {
        if (!response.ok) throw new Error("The association list could not be loaded.");
        const payload = await response.json();
        return Array.isArray(payload) ? payload : payload.data ?? [];
      })
      .then((data) => active && setAssociations(data))
      .catch((reason) => active && setError(reason.message));
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    if (!canLoadEntries) {
      setEntries([]);
      setLoading(false);
      return () => { active = false; };
    }
    setLoading(true); setError("");
    const query = new URLSearchParams({ season_id: seasonId, association_id: associationId });
    fetch(apiPath(`/api/${type}-list?${query}`))
      .then(async (response) => {
        if (!response.ok) throw new Error(`The ${type} list could not be loaded.`);
        const payload = await response.json();
        return Array.isArray(payload) ? payload : payload.data ?? [];
      })
      .then((data) => active && setEntries(data))
      .catch((reason) => active && setError(reason.message))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [type, seasonId, associationId, canLoadEntries]);

  const entityChoices = entries.filter((entry, index) => entries.findIndex((candidate) => entityKey(candidate) === entityKey(entry)) === index);
  const resultEntries = entries.filter((entry) => entityKey(entry) === selectedEntityKey);
  const applyFocus = (uuid) => {
    const nextFocus = { type, uuid };
    window.localStorage.setItem("sams-score-board:focus", JSON.stringify(nextFocus));
    onFocus(nextFocus);
  };

  return <Box component="main">
    <Stack spacing={1} mb={4}>
      <Typography color="primary" fontWeight={700} variant="overline">Choose a focus</Typography>
      <Typography variant="h4" component="h1">Select a {typeLabels.singular}</Typography>
      <Typography color="text.secondary" maxWidth={640}>Choose a season, association, and {typeLabels.singular}; then select its UUID as the focus for following scoreboard views.</Typography>
    </Stack>
    <Card variant="outlined" sx={{ mb: 3 }}><CardContent><Stack spacing={2}>
      <FormControl fullWidth disabled={seasonLoading || seasons.length === 0}>
        <InputLabel id="season-label">Season</InputLabel>
        <Select labelId="season-label" label="Season" value={seasonId} onChange={(event) => { setSeasonId(event.target.value); setAssociationId(""); setSelectedEntityKey(""); }}>
          {seasons.map((season) => <MenuItem key={season.uuid} value={season.uuid}>{season.name || season.uuid}{(season.currentSeason || season.current) ? " (current)" : ""}</MenuItem>)}
        </Select>
      </FormControl>
      <FormControl fullWidth required disabled={!seasonId || associations.length === 0}>
        <InputLabel id="association-label">Association</InputLabel>
        <Select labelId="association-label" label="Association" value={associationId} onChange={(event) => { setAssociationId(event.target.value); setSelectedEntityKey(""); }}>
          {associations.map((association) => <MenuItem key={association.uuid} value={association.uuid} sx={{ pl: 2 + (association.depth ?? 0) * 3 }}>
            {[association.shortname, association.name].filter(Boolean).join(" · ") || association.uuid}
          </MenuItem>)}
        </Select>
      </FormControl>
      <FormControl fullWidth disabled={!canLoadEntries || loading}>
        <InputLabel id="entity-label">{typeLabels.plural}</InputLabel>
        <Select labelId="entity-label" label={typeLabels.plural} value={selectedEntityKey} onChange={(event) => setSelectedEntityKey(event.target.value)}>
          <MenuItem value=""><em>Select a {typeLabels.singular}</em></MenuItem>
          {entityChoices.map((entry) => <MenuItem key={entityKey(entry)} value={entityKey(entry)}>
            {[entry.shortname, entry.name].filter(Boolean).join(" · ") || entry.uuid}
          </MenuItem>)}
        </Select>
      </FormControl>
    </Stack></CardContent></Card>
    {selectedEntityKey && !loading && !error && <Box>
      <Typography variant="h6" mb={1}>Resulting UUIDs</Typography>
      {resultEntries.length === 0 ? <Alert severity="info">No UUIDs match this selection.</Alert> : <List disablePadding sx={{ border: 1, borderColor: "divider", borderRadius: 1, maxHeight: 360, overflow: "auto" }}>
        {resultEntries.map((entry) => <ListItem key={entry.uuid} divider secondaryAction={<Button variant="contained" size="small" onClick={() => applyFocus(entry.uuid)}>Apply</Button>}>
          <ListItemText primary={entry.uuid} secondary={[entry.gender, entry.shortname, entry.name].filter(Boolean).join(" · ")} primaryTypographyProps={{ sx: { overflowWrap: "anywhere", pr: 10 } }} />
        </ListItem>)}
      </List>}
    </Box>}
    {error && <Alert severity="info">{error}</Alert>}
  </Box>;
}

export default function App() {
  const [type, setType] = useState("competition");
  const [menuAnchor, setMenuAnchor] = useState(null);
  const [focus, setFocus] = useState(readFocus);
  const chooseType = (nextType) => { setType(nextType); setMenuAnchor(null); };
  return <Box minHeight="100vh">
    <AppBar position="sticky" elevation={0}><Toolbar>
      <Button color="inherit" onClick={(event) => setMenuAnchor(event.currentTarget)} sx={{ minWidth: 0, mr: 1 }} aria-label="Open selection menu" aria-haspopup="menu"><MenuIcon /></Button>
      <SportsVolleyballIcon sx={{ mr: 1.25 }} />
      <Typography variant="h6">SAMS Score Board</Typography>
      <Menu anchorEl={menuAnchor} open={Boolean(menuAnchor)} onClose={() => setMenuAnchor(null)}><MenuItem selected={type === "competition"} onClick={() => chooseType("competition")}>Select a competition</MenuItem><MenuItem selected={type === "league"} onClick={() => chooseType("league")}>Select a league</MenuItem></Menu>
      {focus && <Chip label={`Focus: ${focus.type} · ${focus.uuid.slice(0, 8)}…`} color="secondary" size="small" sx={{ ml: "auto", maxWidth: { xs: 170, sm: "none" } }} />}
    </Toolbar></AppBar>
    <Container maxWidth="lg" sx={{ py: { xs: 3, md: 5 } }}><SelectorPage key={type} type={type} onFocus={setFocus} /></Container>
  </Box>;
}
