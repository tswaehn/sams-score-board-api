import { useEffect, useState } from "react";
import MenuIcon from "@mui/icons-material/Menu";
import SportsVolleyballIcon from "@mui/icons-material/SportsVolleyball";
import { Alert, AppBar, Avatar, Box, Button, Card, CardContent, Container, FormControl, InputLabel, List, ListItem, ListItemText, Menu, MenuItem, Select, Stack, Toolbar, Typography } from "@mui/material";
import LeagueTable from "./components/LeagueTable.jsx";
import LeagueMatchDays from "./components/LeagueMatchDays.jsx";
import LeagueMatches from "./components/LeagueMatches.jsx";
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
  return [entry.shortname, entry.name].filter(Boolean).join("\u0000") || entry.uuid;
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
  const applyFocus = (entry) => {
    const nextFocus = { type, uuid: entry.uuid, name: entry.name || entry.shortname || entry.shortName || "Unnamed selection" };
    window.localStorage.setItem("sams-score-board:focus", JSON.stringify(nextFocus));
    onFocus(nextFocus);
  };

  return <Box component="main">
    <Stack spacing={1} mb={4}>
      <Typography color="primary" fontWeight={700} variant="overline">Choose a focus</Typography>
      <Typography variant="h4" component="h1">Select a {typeLabels.singular}</Typography>
      <Typography color="text.secondary" maxWidth={640}>Choose a season, association, and {typeLabels.singular}; then apply one of the matching entries as the focus for following scoreboard views.</Typography>
    </Stack>
    <Card variant="outlined" sx={{ mb: 3 }}><CardContent><Stack spacing={2}>
      <FormControl fullWidth disabled={seasonLoading || seasons.length === 0}>
        <InputLabel id="season-label">Season</InputLabel>
        <Select labelId="season-label" label="Season" value={seasonId} onChange={(event) => { setSeasonId(event.target.value); setAssociationId(""); setSelectedEntityKey(""); }}>
          {seasons.map((season) => <MenuItem key={season.uuid} value={season.uuid}>{season.name || "Unnamed season"}{(season.currentSeason || season.current) ? " (current)" : ""}</MenuItem>)}
        </Select>
      </FormControl>
      <FormControl fullWidth required disabled={!seasonId || associations.length === 0}>
        <InputLabel id="association-label">Association</InputLabel>
        <Select labelId="association-label" label="Association" value={associationId} onChange={(event) => { setAssociationId(event.target.value); setSelectedEntityKey(""); }}>
          {associations.map((association) => <MenuItem key={association.uuid} value={association.uuid} sx={{ pl: 2 + (association.depth ?? 0) * 3 }}>
            {[association.shortname, association.name].filter(Boolean).join(" · ") || "Unnamed association"}
          </MenuItem>)}
        </Select>
      </FormControl>
      <FormControl fullWidth disabled={!canLoadEntries || loading}>
        <InputLabel id="entity-label">{typeLabels.plural}</InputLabel>
        <Select labelId="entity-label" label={typeLabels.plural} value={selectedEntityKey} onChange={(event) => setSelectedEntityKey(event.target.value)}>
          <MenuItem value=""><em>Select a {typeLabels.singular}</em></MenuItem>
          {entityChoices.map((entry) => <MenuItem key={entityKey(entry)} value={entityKey(entry)}>
            {[entry.shortname, entry.name].filter(Boolean).join(" · ") || "Unnamed entry"}
          </MenuItem>)}
        </Select>
      </FormControl>
    </Stack></CardContent></Card>
    {selectedEntityKey && !loading && !error && <Box>
      <Typography variant="h6" mb={1}>Available entries</Typography>
      {resultEntries.length === 0 ? <Alert severity="info">No entries match this selection.</Alert> : <List disablePadding sx={{ border: 1, borderColor: "divider", borderRadius: 1, maxHeight: 360, overflow: "auto" }}>
        {resultEntries.map((entry) => <ListItem key={entry.uuid} divider secondaryAction={<Button variant="contained" size="small" onClick={() => applyFocus(entry)}>Apply</Button>}>
          <ListItemText primary={entry.gender || "Unspecified"} secondary={[entry.shortname, entry.name].filter(Boolean).join(" · ")} />
        </ListItem>)}
      </List>}
    </Box>}
    {error && <Alert severity="info">{error}</Alert>}
  </Box>;
}

function TeamsPage({ focus }) {
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!focus) {
      setLoading(false);
      return undefined;
    }
    let active = true;
    setLoading(true);
    setError("");
    fetch(apiPath(`/api/${focus.type}/${focus.uuid}/teams`))
      .then(async (response) => {
        if (!response.ok) throw new Error("The teams could not be loaded.");
        const payload = await response.json();
        return Array.isArray(payload) ? payload : payload.data ?? [];
      })
      .then((data) => active && setTeams(data))
      .catch((reason) => active && setError(reason.message))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [focus]);

  if (!focus) return <Alert severity="info">Choose a competition or league before opening its teams.</Alert>;

  return <Box component="main">
    <Typography variant="h4" component="h1" mb={4}>Teams</Typography>
    {loading && <Typography color="text.secondary">Loading teams…</Typography>}
    {error && <Alert severity="error">{error}</Alert>}
    {!loading && !error && teams.length === 0 && <Alert severity="info">No teams are available for this {focus.type}.</Alert>}
    {!loading && !error && teams.length > 0 && <List disablePadding sx={{ border: 1, borderColor: "divider", borderRadius: 1 }}>
      {teams.map((team) => <ListItem key={team.uuid} divider>
        {team.logoImageForScreenOutputLink || team.logoImageLink ? <Box component="img" src={team.logoImageForScreenOutputLink || team.logoImageLink} alt={team.name || team.shortName || team.shortname || "Team"} sx={{ width: 40, height: 40, mr: 2, objectFit: "contain" }} /> : <Avatar sx={{ mr: 2 }}>
          {(team.name || team.shortName || team.shortname || "?").slice(0, 1)}
        </Avatar>}
        <ListItemText primary={team.name || team.shortName || team.shortname || "Unnamed team"} secondary={team.shortName || team.shortname || undefined} />
      </ListItem>)}
    </List>}
  </Box>;
}

function PlanPage({ focus }) {
  const [rankings, setRankings] = useState([]);
  const [matchDays, setMatchDays] = useState([]);
  const [selectedMatchDay, setSelectedMatchDay] = useState("");
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(focus?.type === "league");
  const [matchesLoading, setMatchesLoading] = useState(false);
  const [matchesError, setMatchesError] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (focus?.type !== "league") return undefined;
    let active = true;
    setLoading(true);
    setError("");
    const getData = async (path, label) => {
      const response = await fetch(apiPath(path));
      if (!response.ok) throw new Error(`The ${label} could not be loaded.`);
      const payload = await response.json();
      return Array.isArray(payload) ? payload : payload.data ?? [];
    };
    Promise.all([
      getData(`/api/league/${focus.uuid}/rankings`, "league table"),
      getData(`/api/league/${focus.uuid}/match-days`, "match days"),
    ])
      .then(([rankingData, matchDayData]) => {
        if (!active) return;
        setRankings(rankingData);
        setMatchDays(matchDayData);
        setSelectedMatchDay((current) => matchDayData.some((matchDay) => matchDay.uuid === current) ? current : matchDayData[0]?.uuid ?? "");
      })
      .catch((reason) => active && setError(reason.message))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [focus]);

  useEffect(() => {
    if (focus?.type !== "league" || !selectedMatchDay) {
      setMatches([]);
      return undefined;
    }
    let active = true;
    setMatchesLoading(true);
    setMatchesError("");
    fetch(apiPath(`/api/league/${focus.uuid}/matches?match_day_id=${encodeURIComponent(selectedMatchDay)}`))
      .then(async (response) => {
        if (!response.ok) throw new Error("The matches could not be loaded.");
        const payload = await response.json();
        return Array.isArray(payload) ? payload : payload.data ?? [];
      })
      .then((data) => active && setMatches(data))
      .catch((reason) => active && setMatchesError(reason.message))
      .finally(() => active && setMatchesLoading(false));
    return () => { active = false; };
  }, [focus, selectedMatchDay]);

  return <Box component="main">
    <Typography variant="h4" component="h1" mb={4}>Plan</Typography>
    {focus?.type !== "league" && <Alert severity="info">Plan data has not been connected to API 2.0 for competitions yet.</Alert>}
    {focus?.type === "league" && loading && <Typography color="text.secondary">Loading league table…</Typography>}
    {focus?.type === "league" && error && <Alert severity="error">{error}</Alert>}
    {focus?.type === "league" && !loading && !error && rankings.length === 0 && matchDays.length === 0 && <Alert severity="info">No plan data is available yet.</Alert>}
    {focus?.type === "league" && !loading && !error && <Stack spacing={4}>
      {rankings.length > 0 && <Box><Typography variant="h6" mb={2}>League table</Typography><LeagueTable rankings={rankings} /></Box>}
      {matchDays.length > 0 && <Box><Typography variant="h6" mb={2}>Match days</Typography><LeagueMatchDays matchDays={matchDays} selectedUuid={selectedMatchDay} onSelect={setSelectedMatchDay} /></Box>}
      {selectedMatchDay && <Box><Typography variant="h6" mb={2}>Matches</Typography>
        {matchesLoading && <Typography color="text.secondary">Loading matches…</Typography>}
        {matchesError && <Alert severity="error">{matchesError}</Alert>}
        {!matchesLoading && !matchesError && matches.length === 0 && <Alert severity="info">No matches are available for this match day.</Alert>}
        {!matchesLoading && !matchesError && matches.length > 0 && <LeagueMatches matches={matches} />}
      </Box>}
    </Stack>}
  </Box>;
}

export default function App() {
  const [type, setType] = useState("competition");
  const [menuAnchor, setMenuAnchor] = useState(null);
  const [focus, setFocus] = useState(readFocus);
  const [page, setPage] = useState("selector");
  const chooseType = (nextType) => { setType(nextType); setPage("selector"); setMenuAnchor(null); };
  const applyFocus = (nextFocus) => { setFocus(nextFocus); setPage("teams"); };
  const title = page === "selector" ? "Selection in progress" : focus?.name || "SAMS Score Board";

  useEffect(() => {
    if (!focus || focus.name) return undefined;
    let active = true;
    fetch(apiPath(`/api/${focus.type}/${focus.uuid}`))
      .then((response) => response.ok ? response.json() : null)
      .then((entity) => {
        const name = entity?.name || entity?.shortname || entity?.shortName;
        if (!active || !name) return;
        const nextFocus = { ...focus, name };
        window.localStorage.setItem("sams-score-board:focus", JSON.stringify(nextFocus));
        setFocus(nextFocus);
      })
      .catch(() => {});
    return () => { active = false; };
  }, [focus]);
  return <Box minHeight="100vh" display="flex" flexDirection="column">
    <AppBar position="sticky" elevation={0}><Toolbar>
      <Button color="inherit" onClick={(event) => setMenuAnchor(event.currentTarget)} sx={{ minWidth: 0, mr: 1 }} aria-label="Open selection menu" aria-haspopup="menu"><MenuIcon /></Button>
      <SportsVolleyballIcon sx={{ mr: 1.25 }} />
      <Typography variant="h6" noWrap>{title}</Typography>
      <Menu anchorEl={menuAnchor} open={Boolean(menuAnchor)} onClose={() => setMenuAnchor(null)}><MenuItem selected={page === "selector" && type === "competition"} onClick={() => chooseType("competition")}>Select a competition</MenuItem><MenuItem selected={page === "selector" && type === "league"} onClick={() => chooseType("league")}>Select a league</MenuItem></Menu>
      {focus && <Stack direction="row" spacing={0.5} sx={{ ml: "auto" }}>
        <Button color="inherit" onClick={() => setPage("teams")} sx={{ textTransform: "none", bgcolor: page === "teams" ? "rgba(255,255,255,0.18)" : "transparent", "&:hover": { bgcolor: "rgba(255,255,255,0.24)" } }}>Team</Button>
        <Button color="inherit" onClick={() => setPage("plan")} sx={{ textTransform: "none", bgcolor: page === "plan" ? "rgba(255,255,255,0.18)" : "transparent", "&:hover": { bgcolor: "rgba(255,255,255,0.24)" } }}>Plan</Button>
      </Stack>}
    </Toolbar></AppBar>
    <Container maxWidth="lg" sx={{ py: { xs: 3, md: 5 }, flexGrow: 1 }}>{page === "teams" ? <TeamsPage focus={focus} /> : page === "plan" ? <PlanPage focus={focus} /> : <SelectorPage key={type} type={type} onFocus={applyFocus} />}</Container>
    <Box component="footer" sx={{ borderTop: 1, borderColor: "divider", bgcolor: "background.paper", py: 2 }}>
      <Container maxWidth="lg">
        <Typography variant="body2" color="text.secondary">
          Focus: {focus ? `${focus.type} · ${focus.uuid}` : "No competition or league selected"}
        </Typography>
      </Container>
    </Box>
  </Box>;
}
