import { useEffect, useState } from "react";
import { Alert, Box, Stack, Typography } from "@mui/material";
import { getApiData } from "../api.js";
import LeagueTable from "../components/LeagueTable.jsx";
import LeagueMatchDays from "../components/LeagueMatchDays.jsx";
import LeagueMatches from "../components/LeagueMatches.jsx";
import CompetitionTable from "../components/CompetitionTable.jsx";
import CompetitionMatchGroups from "../components/CompetitionMatchGroups.jsx";
import CompetitionMatches from "../components/CompetitionMatches.jsx";

function CompetitionPlan({ focus }) {
  const [groups, setGroups] = useState([]), [rankingGroups, setRankingGroups] = useState([]), [selectedGroup, setSelectedGroup] = useState(""), [matches, setMatches] = useState([]), [loading, setLoading] = useState(true), [matchesLoading, setMatchesLoading] = useState(false), [error, setError] = useState("");
  useEffect(() => { let active = true; setLoading(true); Promise.all([getApiData(`/api/competition/${focus.uuid}/match-groups`, "match groups"), getApiData(`/api/competition/${focus.uuid}/rankings`, "competition table")]).then(([g, r]) => { if (active) { setGroups(g); setRankingGroups(r); setSelectedGroup(g[0]?.uuid ?? ""); } }).catch((e) => active && setError(e.message)).finally(() => active && setLoading(false)); return () => { active = false; }; }, [focus]);
  useEffect(() => { if (!selectedGroup) return undefined; let active = true; setMatchesLoading(true); getApiData(`/api/competition/${focus.uuid}/matches?match_group_id=${encodeURIComponent(selectedGroup)}`, "matches").then((data) => active && setMatches(data)).catch((e) => active && setError(e.message)).finally(() => active && setMatchesLoading(false)); return () => { active = false; }; }, [focus, selectedGroup]);
  const group = groups.find((item) => item.uuid === selectedGroup); const ranking = rankingGroups.find((item) => item.matchGroupName === group?.name);
  if (loading) return <Typography color="text.secondary">Loading competition plan…</Typography>; if (error) return <Alert severity="error">{error}</Alert>;
  return <Stack spacing={4}>{selectedGroup && <Box><Typography variant="h6" mb={2}>Competition table</Typography><CompetitionTable rankingGroup={ranking} /></Box>}{groups.length > 0 && <Box><Typography variant="h6" mb={2}>Match groups</Typography><CompetitionMatchGroups groups={groups} selectedUuid={selectedGroup} onSelect={setSelectedGroup} /></Box>}{selectedGroup && <Box><Typography variant="h6" mb={2}>Matches</Typography>{matchesLoading && <Typography color="text.secondary">Loading matches…</Typography>}{!matchesLoading && matches.length === 0 && <Alert severity="info">No matches are available for this match group.</Alert>}{!matchesLoading && matches.length > 0 && <CompetitionMatches matches={matches} />}</Box>}</Stack>;
}

function LeaguePlan({ focus }) {
  const [rankings, setRankings] = useState([]), [matchDays, setMatchDays] = useState([]), [selectedDay, setSelectedDay] = useState(""), [matches, setMatches] = useState([]), [loading, setLoading] = useState(true), [matchesLoading, setMatchesLoading] = useState(false), [error, setError] = useState("");
  useEffect(() => { let active = true; setLoading(true); Promise.all([getApiData(`/api/league/${focus.uuid}/rankings`, "league table"), getApiData(`/api/league/${focus.uuid}/match-days`, "match days")]).then(([r, d]) => { if (active) { setRankings(r); setMatchDays(d); setSelectedDay(d[0]?.uuid ?? ""); } }).catch((e) => active && setError(e.message)).finally(() => active && setLoading(false)); return () => { active = false; }; }, [focus]);
  useEffect(() => { if (!selectedDay) return undefined; let active = true; setMatchesLoading(true); getApiData(`/api/league/${focus.uuid}/matches?match_day_id=${encodeURIComponent(selectedDay)}`, "matches").then((data) => active && setMatches(data)).catch((e) => active && setError(e.message)).finally(() => active && setMatchesLoading(false)); return () => { active = false; }; }, [focus, selectedDay]);
  if (loading) return <Typography color="text.secondary">Loading league plan…</Typography>; if (error) return <Alert severity="error">{error}</Alert>;
  return <Stack spacing={4}>{rankings.length > 0 && <Box><Typography variant="h6" mb={2}>League table</Typography><LeagueTable rankings={rankings} /></Box>}{matchDays.length > 0 && <Box><Typography variant="h6" mb={2}>Match days</Typography><LeagueMatchDays matchDays={matchDays} selectedUuid={selectedDay} onSelect={setSelectedDay} /></Box>}{selectedDay && <Box><Typography variant="h6" mb={2}>Matches</Typography>{matchesLoading && <Typography color="text.secondary">Loading matches…</Typography>}{!matchesLoading && matches.length === 0 && <Alert severity="info">No matches are available for this match day.</Alert>}{!matchesLoading && matches.length > 0 && <LeagueMatches matches={matches} />}</Box>}</Stack>;
}

export default function PlanPage({ focus }) { return <Box component="main"><Typography variant="h4" component="h1" mb={4}>Plan</Typography>{focus?.type === "competition" ? <CompetitionPlan focus={focus} /> : focus?.type === "league" ? <LeaguePlan focus={focus} /> : <Alert severity="info">Choose an entity first.</Alert>}</Box>; }
