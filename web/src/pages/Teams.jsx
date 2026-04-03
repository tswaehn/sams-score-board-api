import { useEffect, useState } from "react";
import { Avatar, Box, Paper, Stack, Typography } from "@mui/material";
import { fetchJson, getTeamShortName } from "../api/api.js";

export default function Teams() {
  const [teams, setTeams] = useState([]);
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    fetchJson("/api/teams")
      .then((data) => {
        if (isMounted) {
          setTeams(data.teams);
          setMeta({
            competition: data.competition,
            association: data.association,
            season: data.season
          });
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

      {loading && (
        <Typography color="text.secondary">Loading teams...</Typography>
      )}
      {error && (
        <Typography color="error" sx={{ fontWeight: 600 }}>
          {error}
        </Typography>
      )}

      {!loading && !error && (
        <Paper
          elevation={0}
          sx={{
            p: 2,
            borderRadius: 3,
            border: "1px solid rgba(20, 17, 15, 0.08)",
            bgcolor: "background.paper",
            gap: 2
          }}
        >
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            Setzliste
          </Typography>
          {meta && (
            <Typography color="text.secondary">
              {meta.competition.name} · {meta.association.name} · {meta.season.name}
            </Typography>
          )}

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
                  bgcolor: "teamInfo.main"
                }}
              >
                <Avatar
                  src={team.logo_url}
                  alt={`${team.name} logo`}
                  sx={{ width: 56, height: 56, bgcolor: "#f3ebe0" }}
                />
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    {team.name}
                  </Typography>
                  <Typography variant="subtitle2" color="text.secondary">
                    {getTeamShortName(team.name, team.short_name)}
                  </Typography>
                </Box>
              </Paper>
            ))}
          </Stack>
        </Paper>
      )}
    </Box>
  );
}
