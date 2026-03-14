import { useEffect, useState } from "react";
import { Avatar, Box, Paper, Stack, Typography } from "@mui/material";
import { fetchJson } from "../api/mockApi.js";

export default function Teams() {
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    fetchJson("/api/teams")
      .then((data) => {
        if (isMounted) {
          setTeams(data.teams);
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

  return (
    <Box sx={{ display: "grid", gap: 2 }}>
      <Box>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 0.5 }}>
          Teams
        </Typography>
        <Typography color="text.secondary">
          Active rosters and status snapshots.
        </Typography>
      </Box>

      {loading && (
        <Typography color="text.secondary">Loading teams...</Typography>
      )}
      {error && (
        <Typography color="error" sx={{ fontWeight: 600 }}>
          {error}
        </Typography>
      )}

      {!loading && !error && (
        <Stack spacing={1.2}>
          {teams.map((team) => (
            <Paper
              key={team.uuid}
              elevation={0}
              sx={{
                p: 1.5,
                display: "flex",
                alignItems: "center",
                gap: 2,
                borderRadius: 2.5,
                border: "1px solid rgba(20, 17, 15, 0.08)",
                bgcolor: "background.paper"
              }}
            >
              <Avatar
                src={team.logo_url}
                alt={`${team.name} logo`}
                sx={{ width: 56, height: 56, bgcolor: "#f3ebe0" }}
              />
              <Box>
                <Typography variant="subtitle2" color="text.secondary">
                  {team.short_name}
                </Typography>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  {team.name}
                </Typography>
              </Box>
            </Paper>
          ))}
        </Stack>
      )}
    </Box>
  );
}
