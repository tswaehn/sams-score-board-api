import { useEffect, useState } from "react";
import { Box, Chip, Paper, Stack, Typography } from "@mui/material";
import { fetchJson } from "../api/index.js";

export default function Live() {
  const [competition, setCompetition] = useState(null);
  const [association, setAssociation] = useState(null);
  const [season, setSeason] = useState(null);
  const [matchGroups, setMatchGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    fetchJson("/api/live")
      .then((data) => {
        if (isMounted) {
          setCompetition(data.competition);
          setAssociation(data.association);
          setSeason(data.season);
          setMatchGroups(data.matchGroups);
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
      {loading && <Typography color="text.secondary">Loading live feed...</Typography>}
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
              bgcolor: "background.paper",
              display: "grid",
              gap: 1
            }}
          >
            <Typography variant="h5" sx={{ fontWeight: 700 }}>
              {competition?.name}
            </Typography>
            <Typography color="text.secondary">
              {association?.name} · {season?.name}
            </Typography>
            <Typography color="text.secondary">
              The current mock payload does not include live court scores. This page
              now reflects the available competition metadata and match groups.
            </Typography>
          </Paper>

          <Paper
            elevation={0}
            sx={{
              p: 2,
              borderRadius: 3,
              border: "1px solid rgba(20, 17, 15, 0.08)",
              bgcolor: "background.paper"
            }}
          >
            <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
              {matchGroups.map((matchGroup) => (
                <Chip
                  key={matchGroup.uuid}
                  label={`${matchGroup.name} · Level ${matchGroup.tourneyLevel}`}
                  sx={{
                    background: "teamInfo.main",
                    color: "primary.main",
                    fontWeight: 600
                  }}
                />
              ))}
            </Stack>
          </Paper>
        </>
      )}
    </Box>
  );
}
