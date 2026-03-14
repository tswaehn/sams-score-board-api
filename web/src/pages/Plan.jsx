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
import { fetchJson } from "../api/mockApi.js";

export default function Plan() {
  const [stages, setStages] = useState([]);
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeStageId, setActiveStageId] = useState(null);

  useEffect(() => {
    let isMounted = true;

    Promise.all([fetchJson("/api/plan"), fetchJson("/api/teams")])
      .then(([planData, teamData]) => {
        if (isMounted) {
          setStages(planData.stages);
          setTeams(teamData.teams);
          setActiveStageId(planData.stages[0]?.id ?? null);
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

  const teamById = useMemo(() => {
    const map = new Map();
    teams.forEach((team) => map.set(team.uuid, team));
    return map;
  }, [teams]);

  const activeStage = stages.find((stage) => stage.id === activeStageId);

  return (
    <Box sx={{ display: "grid", gap: 2 }}>
      <Box>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 0.5 }}>
          Plan
        </Typography>
        <Typography color="text.secondary">
          Stages and group standings.
        </Typography>
      </Box>

      {loading && (
        <Typography color="text.secondary">Loading plan...</Typography>
      )}
      {error && (
        <Typography color="error" sx={{ fontWeight: 600 }}>
          {error}
        </Typography>
      )}

      {!loading && !error && (
        <Box sx={{ display: "grid", gap: 2 }}>
          <Tabs
            value={activeStageId}
            onChange={(_, value) => setActiveStageId(value)}
            variant="scrollable"
            allowScrollButtonsMobile
            textColor="inherit"
            indicatorColor="secondary"
          >
            {stages.map((stage) => (
              <Tab key={stage.id} value={stage.id} label={stage.name} />
            ))}
          </Tabs>

          {activeStage && (
            <Paper
              elevation={0}
              sx={{
                p: 3,
                borderRadius: 3,
                border: "1px solid rgba(20, 17, 15, 0.08)",
                background: "#fffdf8",
                display: "grid",
                gap: 2
              }}
            >
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                {activeStage.name}
              </Typography>

              {activeStage.groups && (
                <Stack spacing={2}>
                  {activeStage.groups.map((group) => (
                    <Paper
                      key={group.id}
                      elevation={0}
                      sx={{
                        p: 2,
                        borderRadius: 2.5,
                        border: "1px solid rgba(20, 17, 15, 0.08)",
                        background: "white"
                      }}
                    >
                      <Typography
                        variant="subtitle1"
                        sx={{ fontWeight: 700, mb: 1.5 }}
                      >
                        Gruppe {group.name}
                      </Typography>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Team</TableCell>
                            <TableCell align="right">Spiele</TableCell>
                            <TableCell align="right">S/N</TableCell>
                            <TableCell align="right">Sätze</TableCell>
                            <TableCell align="right">Bälle</TableCell>
                            <TableCell align="right">Punkte</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {group.teams.map((team) => {
                            const meta = teamById.get(team.uuid);
                            return (
                              <TableRow key={team.uuid} hover>
                                <TableCell>
                                  <Stack
                                    direction="row"
                                    spacing={1.5}
                                    alignItems="center"
                                  >
                                    <Avatar
                                      src={meta?.logo_url}
                                      alt={`${meta?.name ?? "Team"} logo`}
                                      sx={{ width: 36, height: 36, bgcolor: "#f3ebe0" }}
                                    />
                                    <Typography sx={{ fontWeight: 600 }}>
                                      {meta ? meta.name : "Unknown team"}
                                    </Typography>
                                  </Stack>
                                </TableCell>
                                <TableCell align="right">{team.played}</TableCell>
                                <TableCell align="right">
                                  {team.wins}/{team.lost}
                                </TableCell>
                                <TableCell align="right">
                                  {team.sets_won}:{team.sets_lost}
                                </TableCell>
                                <TableCell align="right">
                                  {team.ball_points_won}:{team.ball_points_lost}
                                </TableCell>
                                <TableCell align="right">{team.points}</TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </Paper>
                  ))}
                </Stack>
              )}

              {activeStage.matches && (
                <Stack spacing={1.2}>
                  {activeStage.matches.map((match) => {
                    const home = teamById.get(match.home_uuid);
                    const away = teamById.get(match.away_uuid);
                    return (
                      <Paper
                        key={match.id}
                        elevation={0}
                        sx={{
                          p: 1.6,
                          borderRadius: 2.5,
                          border: "1px solid rgba(20, 17, 15, 0.08)",
                          background: "white",
                          display: "grid",
                          gridTemplateColumns: "1fr auto 1fr",
                          alignItems: "center",
                          gap: 2
                        }}
                      >
                        <Stack direction="row" spacing={1.5} alignItems="center">
                          <Avatar
                            src={home?.logo_url}
                            alt={`${home?.name ?? "Team"} logo`}
                            sx={{ width: 32, height: 32, bgcolor: "#f3ebe0" }}
                          />
                          <Typography sx={{ fontWeight: 600 }}>
                            {home ? home.name : "Unknown team"}
                          </Typography>
                        </Stack>
                        <Typography
                          variant="h6"
                          sx={{ fontWeight: 700, color: "primary.main" }}
                        >
                          {match.sets_home}:{match.sets_away}
                        </Typography>
                        <Stack
                          direction="row"
                          spacing={1.5}
                          alignItems="center"
                          justifyContent="flex-end"
                        >
                          <Typography sx={{ fontWeight: 600 }}>
                            {away ? away.name : "Unknown team"}
                          </Typography>
                          <Avatar
                            src={away?.logo_url}
                            alt={`${away?.name ?? "Team"} logo`}
                            sx={{ width: 32, height: 32, bgcolor: "#f3ebe0" }}
                          />
                        </Stack>
                      </Paper>
                    );
                  })}
                </Stack>
              )}
            </Paper>
          )}
        </Box>
      )}
    </Box>
  );
}
