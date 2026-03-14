import { useEffect, useMemo, useState } from "react";
import {
  Avatar,
  Box,
  Chip,
  Divider,
  Paper,
  Stack,
  Typography
} from "@mui/material";
import { fetchJson } from "../api/mockApi.js";

export default function Live() {
  const [courts, setCourts] = useState([]);
  const [stats, setStats] = useState([]);
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    Promise.all([fetchJson("/api/live"), fetchJson("/api/teams")])
      .then(([liveData, teamData]) => {
        if (isMounted) {
          setCourts(liveData.courts);
          setStats(liveData.stats);
          setTeams(teamData.teams);
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

  return (
    <Box sx={{ display: "grid", gap: 2 }}>

      {loading && (
        <Typography color="text.secondary">Loading live feed...</Typography>
      )}
      {error && (
        <Typography color="error" sx={{ fontWeight: 600 }}>
          {error}
        </Typography>
      )}

      {!loading && !error && (
        <>
          <Paper
            elevation={0}
            sx={{
              p: 2,
              borderRadius: 3,
              border: "1px solid rgba(20, 17, 15, 0.08)",
              bgcolor: "background.paper"
            }}
          >
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" },
                gap: 2
              }}
            >
              {courts.map((court) => {
                const home = teamById.get(court.match.home_uuid);
                const away = teamById.get(court.match.away_uuid);
                return (
                  <Paper
                    key={court.id}
                    elevation={0}
                    sx={{
                      p: 2.5,
                      borderRadius: 3,
                      border: "1px solid rgba(20, 17, 15, 0.08)",
                      bgcolor: "teamInfo.main",
                      display: "grid",
                      gap: 2
                    }}
                  >
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Chip
                        label={court.name}
                        sx={{
                          background: "rgba(38, 70, 83, 0.1)",
                          color: "primary.main",
                          fontWeight: 600
                        }}
                      />
                      <Chip
                        label={court.match.status}
                        size="small"
                        sx={{
                          background: "rgba(228, 87, 46, 0.12)",
                          color: "secondary.main",
                          fontWeight: 600,
                          textTransform: "uppercase"
                        }}
                      />
                    </Stack>

                    <Stack spacing={1.5} sx={{ bgcolor: "teamInfo.main" }}>
                      <Stack direction="row" spacing={1.5} alignItems="center">
                        <Avatar
                          src={home?.logo_url}
                          alt={`${home?.name ?? "Team"} logo`}
                          sx={{ width: 40, height: 40, bgcolor: "#f3ebe0" }}
                        />
                        <Box sx={{ flex: 1 }}>
                          <Typography sx={{ fontWeight: 600 }}>
                            {home ? home.name : "Unknown team"}
                          </Typography>
                          <Typography color="text.secondary" variant="body2">
                            Sets {court.match.sets_home}
                          </Typography>
                        </Box>
                        <Typography variant="h5" sx={{ fontWeight: 700 }}>
                          {court.match.points_home}
                        </Typography>
                      </Stack>
                      <Divider />
                      <Stack direction="row" spacing={1.5} alignItems="center">
                        <Avatar
                          src={away?.logo_url}
                          alt={`${away?.name ?? "Team"} logo`}
                          sx={{ width: 40, height: 40, bgcolor: "#f3ebe0" }}
                        />
                        <Box sx={{ flex: 1 }}>
                          <Typography sx={{ fontWeight: 600 }}>
                            {away ? away.name : "Unknown team"}
                          </Typography>
                          <Typography color="text.secondary" variant="body2">
                            Sets {court.match.sets_away}
                          </Typography>
                        </Box>
                        <Typography variant="h5" sx={{ fontWeight: 700 }}>
                          {court.match.points_away}
                        </Typography>
                      </Stack>
                    </Stack>
                  </Paper>
                );
              })}
            </Box>
          </Paper>


        </>
      )}
    </Box>
  );
}
