import { useEffect, useState } from "react";
import { Avatar, Box, Paper, Stack, Typography } from "@mui/material";
import { useLocation } from "react-router-dom";
import { fetchJson, getTeamShortName } from "../api/api.js";
import { layout } from "../components/layout.js";

export default function EntityTeams({ expectedEntityType }) {
  const location = useLocation();
  const [teams, setTeams] = useState([]);
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    fetchJson("/api/teams")
      .then((data) => {
        if (isMounted) {
          if (expectedEntityType && data.entityType !== expectedEntityType) {
            setError(`Unexpected entity type: ${data.entityType}`);
            setLoading(false);
            return;
          }

          setTeams(data.teams);
          setMeta({
            entityType: data.entityType,
            entity: data.entity,
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
  }, [expectedEntityType, location.pathname]);

  return (
    <Box sx={{ display: "grid", gap: layout.gap.page }}>
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
            p: layout.padding.surface,
            borderRadius: layout.radius.surface,
            border: "1px solid rgba(20, 17, 15, 0.08)",
            bgcolor: "background.paper",
            gap: layout.gap.section
          }}
        >
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            Teams
          </Typography>
          {meta && (
            <Typography color="text.secondary">
              {meta.entity?.name} · {meta.association?.name} · {meta.season?.name}
            </Typography>
          )}

          <Stack spacing={layout.gap.cardList}>
            {teams.map((team) => (
              <Paper
                key={team.uuid}
                elevation={0}
                sx={{
                  p: layout.padding.card,
                  display: "flex",
                  alignItems: "center",
                  gap: layout.gap.cardContent,
                  borderRadius: layout.radius.surface,
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

