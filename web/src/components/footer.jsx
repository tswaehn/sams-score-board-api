import { useEffect, useState } from "react";
import { Box, Container, Link, Typography } from "@mui/material";

export default function Footer() {
  const [competitionUuid, setCompetitionUuid] = useState("");

  useEffect(() => {
    const readCompetitionUuid = () => {
      setCompetitionUuid(window.localStorage.getItem("competition-uuid") ?? "");
    };

    readCompetitionUuid();
    window.addEventListener("storage", readCompetitionUuid);
    window.addEventListener("competition-uuid-updated", readCompetitionUuid);

    return () => {
      window.removeEventListener("storage", readCompetitionUuid);
      window.removeEventListener("competition-uuid-updated", readCompetitionUuid);
    };
  }, []);

  return (
    <Box
      component="footer"
      sx={{
        px: 3,
        py: 2.5,
        borderTop: "1px solid rgba(20, 17, 15, 0.08)",
        bgcolor: "rgba(255, 255, 255, 0.7)"
      }}
    >
      <Container sx={{ display: "flex", justifyContent: "center" }}>
        <Box sx={{ display: "grid", justifyItems: "center", gap: 0.5 }}>
          <Link
            href="/competitions"
            color="text.secondary"
            underline="hover"
            sx={{ fontWeight: 500 }}
          >
            Competition List
          </Link>
          {competitionUuid && (
            <Typography
              variant="body2"
              sx={{ color: "rgba(20, 17, 15, 0.45)", fontWeight: 300 }}
            >
              {competitionUuid}
            </Typography>
          )}
        </Box>
      </Container>
    </Box>
  );
}
