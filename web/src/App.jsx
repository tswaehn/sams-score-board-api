import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { Box, Container, Typography } from "@mui/material";
import CompetitionSelection from "./pages/CompetitionSelection.jsx";
import LeagueSelection from "./pages/LeagueSelection.jsx";
import CompetitionTeams from "./pages/CompetitionTeams.jsx";
import LeagueTeams from "./pages/LeagueTeams.jsx";
import CompetitionPlan from "./pages/CompetitionPlan.jsx";
import LeaguePlan from "./pages/LeaguePlan.jsx";
import CompetitionLive from "./pages/CompetitionLive.jsx";
import LeagueLive from "./pages/LeagueLive.jsx";
import FullScreenCompetition from "./pages/FullScreenCompetition.jsx";
import Header from "./components/header.jsx";
import Footer from "./components/footer.jsx";
import { fetchJson } from "./api/api.js";
import {
  clearSelectedEntity,
  getEntityConfig,
  getSelectedEntity
} from "./entities/entity.js";

function SavedEntityRedirect() {
  const navigate = useNavigate();
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    let isMounted = true;

    const redirectToSavedEntity = async () => {
      const { entityType, entityUuid } = getSelectedEntity();

      if (!entityType || !entityUuid) {
        if (isMounted) {
          setStatus("missing");
          navigate("/competitions", { replace: true });
        }
        return;
      }

      try {
        await fetchJson(`/api/${entityType}/${entityUuid}`);
        const entityConfig = getEntityConfig(entityType);

        if (isMounted) {
          setStatus("ready");
          navigate(`${entityConfig.routeBase}/${entityUuid}/teams`, { replace: true });
        }
      } catch {
        clearSelectedEntity();

        if (isMounted) {
          setStatus("invalid");
          navigate("/competitions", { replace: true });
        }
      }
    };

    redirectToSavedEntity();

    return () => {
      isMounted = false;
    };
  }, [navigate]);

  if (status === "checking") {
    return <Typography color="text.secondary">Loading saved selection...</Typography>;
  }

  return null;
}

export default function App() {
  const location = useLocation();
  const isFullScreenCompetitionRoute = /^\/competition\/[^/]+\/full-screen(?:\/|$)/.test(
    location.pathname
  );

  useEffect(() => {
    if (window.parent === window) {
      return undefined;
    }

    const reportWindowSize = () => {
      window.parent.postMessage(
        {
          type: "sams-score-board:window-size",
          payload: {
            width: window.innerWidth,
            height: window.innerHeight
          }
        },
        "*"
      );
    };

    reportWindowSize();
    window.addEventListener("resize", reportWindowSize);

    return () => {
      window.removeEventListener("resize", reportWindowSize);
    };
  }, []);

  return (
    <Box
      sx={{
        minHeight: "100vh",
        bgcolor: "background.default"
      }}
    >
      <Header />

      <Box
        sx={
          isFullScreenCompetitionRoute
            ? { width: "100%", px: 2, py: 2 }
            : { width: "100%" }
        }
      >
        {isFullScreenCompetitionRoute ? (
          <Routes>
            <Route path="/" element={<SavedEntityRedirect />} />
            <Route path="/competitions" element={<CompetitionSelection />} />
            <Route path="/leagues" element={<LeagueSelection />} />
            <Route path="/competition" element={<SavedEntityRedirect />} />
            <Route path="/competition/" element={<SavedEntityRedirect />} />
            <Route path="/competition/:competitionUuid" element={<Navigate to="teams" replace />} />
            <Route path="/competition/:competitionUuid/teams" element={<CompetitionTeams />} />
            <Route path="/competition/:competitionUuid/plan" element={<CompetitionPlan />} />
            <Route path="/competition/:competitionUuid/live" element={<CompetitionLive />} />
            <Route
              path="/competition/:competitionUuid/full-screen"
              element={<FullScreenCompetition />}
            />
            <Route path="/competition/*" element={<Navigate to="/competitions" replace />} />
            <Route path="/league/:leagueUuid" element={<Navigate to="teams" replace />} />
            <Route path="/league/:leagueUuid/teams" element={<LeagueTeams />} />
            <Route path="/league/:leagueUuid/plan" element={<LeaguePlan />} />
            <Route path="/league/:leagueUuid/live" element={<LeagueLive />} />
            <Route path="/league/*" element={<Navigate to="/leagues" replace />} />
          </Routes>
        ) : (
          <Container sx={{ py: 4 }}>
            <Routes>
              <Route path="/" element={<SavedEntityRedirect />} />
              <Route path="/competitions" element={<CompetitionSelection />} />
              <Route path="/leagues" element={<LeagueSelection />} />
              <Route path="/competition" element={<SavedEntityRedirect />} />
              <Route path="/competition/" element={<SavedEntityRedirect />} />
              <Route
                path="/competition/:competitionUuid"
                element={<Navigate to="teams" replace />}
              />
              <Route path="/competition/:competitionUuid/teams" element={<CompetitionTeams />} />
              <Route path="/competition/:competitionUuid/plan" element={<CompetitionPlan />} />
              <Route path="/competition/:competitionUuid/live" element={<CompetitionLive />} />
              <Route
                path="/competition/:competitionUuid/full-screen"
                element={<FullScreenCompetition />}
              />
              <Route path="/competition/*" element={<Navigate to="/competitions" replace />} />
              <Route path="/league/:leagueUuid" element={<Navigate to="teams" replace />} />
              <Route path="/league/:leagueUuid/teams" element={<LeagueTeams />} />
              <Route path="/league/:leagueUuid/plan" element={<LeaguePlan />} />
              <Route path="/league/:leagueUuid/live" element={<LeagueLive />} />
              <Route path="/league/*" element={<Navigate to="/leagues" replace />} />
            </Routes>
          </Container>
        )}
      </Box>

      <Footer />
    </Box>
  );
}
