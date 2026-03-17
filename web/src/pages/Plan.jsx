import { useEffect, useMemo, useState } from "react";
import {
  Avatar,
  Box,
  Paper,
  Stack,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography
} from "@mui/material";
import { fetchJson } from "../api/index.js";

function getRankingRows(rankings, matchGroupName) {
  const groupRankings = rankings[matchGroupName] ?? {};

  return Object.entries(groupRankings)
    .sort(([left], [right]) => Number(left) - Number(right))
    .map(([rank, entry]) => ({
      rank,
      ...entry
    }));
}

export default function Plan() {
  const [competition, setCompetition] = useState(null);
  const [association, setAssociation] = useState(null);
  const [season, setSeason] = useState(null);
  const [matchGroups, setMatchGroups] = useState([]);
  const [rankings, setRankings] = useState({});
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeMatchGroupId, setActiveMatchGroupId] = useState(null);

  useEffect(() => {
    let isMounted = true;

    fetchJson("/api/plan")
      .then((data) => {
        if (isMounted) {
          setCompetition(data.competition);
          setAssociation(data.association);
          setSeason(data.season);
          setMatchGroups(data.matchGroups);
          setRankings(data.rankings);
          setTeams(data.teams);
          setActiveMatchGroupId(data.matchGroups[0]?.uuid ?? null);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const teamByName = useMemo(() => {
    const map = new Map();

    teams.forEach((team) => {
      map.set(team.name, team);
    });

    return map;
  }, [teams]);

  const activeMatchGroup =
    matchGroups.find((matchGroup) => matchGroup.uuid === activeMatchGroupId) ?? null;
  const rankingRows = activeMatchGroup
    ? getRankingRows(rankings, activeMatchGroup.name)
    : [];

  return (
    <Box sx={{ display: "grid", gap: 2 }}>
      {loading && <Typography color="text.secondary">Loading plan...</Typography>}
      {error && (
        <Typography color="error" sx={{ fontWeight: 600 }}>
          {error}
        </Typography>
      )}

      {!loading && !error && (
        <Box sx={{ display: "grid", gap: 2 }}>
          <Paper
            elevation={0}
            sx={{
              p: 2,
              borderRadius: 3,
              border: "1px solid rgba(20, 17, 15, 0.08)",
              bgcolor: "background.paper"
            }}
          >
            <Typography variant="h5" sx={{ fontWeight: 700 }}>
              {competition?.name}
            </Typography>
            <Typography color="text.secondary">
              {association?.name} · {season?.name}
            </Typography>
          </Paper>

          <Tabs
            value={activeMatchGroupId}
            onChange={(_, value) => setActiveMatchGroupId(value)}
            variant="scrollable"
            allowScrollButtonsMobile
            textColor="inherit"
            indicatorColor="secondary"
          >
            {matchGroups.map((matchGroup) => (
              <Tab key={matchGroup.uuid} value={matchGroup.uuid} label={matchGroup.name} />
            ))}
          </Tabs>

          {activeMatchGroup && (
            <Paper
              elevation={0}
              sx={{
                p: 3,
                borderRadius: 3,
                border: "1px solid rgba(20, 17, 15, 0.08)",
                bgcolor: "background.paper",
                display: "grid",
                gap: 2
              }}
            >
              <Box>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  {activeMatchGroup.name}
                </Typography>
                <Typography color="text.secondary">
                  Tourney level {activeMatchGroup.tourneyLevel}
                </Typography>
              </Box>

              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  borderRadius: 2.5,
                  border: "1px solid rgba(20, 17, 15, 0.08)",
                  bgcolor: "teamInfo.main"
                }}
              >
                <Table size="small">
                  <TableHead sx={{ bgcolor: "teamInfo.main" }}>
                    <TableRow>
                      <TableCell>Rank</TableCell>
                      <TableCell>Team</TableCell>
                      <TableCell align="right">Matches</TableCell>
                      <TableCell align="right">W/L</TableCell>
                      <TableCell align="right">Sets</TableCell>
                      <TableCell align="right">Balls</TableCell>
                      <TableCell align="right">Diff</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {rankingRows.map((row) => {
                      const team = teamByName.get(row.teamName);

                      return (
                        <TableRow key={`${activeMatchGroup.uuid}-${row.rank}`} hover>
                          <TableCell>{row.rank}</TableCell>
                          <TableCell>
                            <Stack direction="row" spacing={1.5} alignItems="center">
                              <Avatar
                                src={team?.logo_url}
                                alt={`${row.teamName} logo`}
                                sx={{ width: 36, height: 36, bgcolor: "#f3ebe0" }}
                              />
                              <Typography sx={{ fontWeight: 600 }}>
                                {row.teamName}
                              </Typography>
                            </Stack>
                          </TableCell>
                          <TableCell align="right">{row.matchesPlayed}</TableCell>
                          <TableCell align="right">
                            {row.wins}/{row.losses}
                          </TableCell>
                          <TableCell align="right">
                            {row.setWins}:{row.setLosses}
                          </TableCell>
                          <TableCell align="right">
                            {row.ballWins}:{row.ballLosses}
                          </TableCell>
                          <TableCell align="right">{row.ballDifference}</TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </Paper>
            </Paper>
          )}
        </Box>
      )}
    </Box>
  );
}
