import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { Box, Container, Typography } from "@mui/material";
import Teams from "./pages/Teams.jsx";
import Plan from "./pages/Plan.jsx";
import Live from "./pages/Live.jsx";
import CompetitionList from "./pages/CompetitionList.jsx";
import Header from "./components/header.jsx";
import Footer from "./components/footer.jsx";
import { fetchJson } from "./api/api.js";

const selectedCompetitionUuidStorageKey = "competition-uuid";

function SavedCompetitionRedirect() {
  const navigate = useNavigate();
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    let isMounted = true;

    const redirectToSavedCompetition = async () => {
      const savedCompetitionUuid = window.localStorage.getItem(
        selectedCompetitionUuidStorageKey
      );

      if (!savedCompetitionUuid) {
        if (isMounted) {
          setStatus("missing");
          navigate("/competitions", { replace: true });
        }
        return;
      }

      try {
        await fetchJson(`/api/competition/${savedCompetitionUuid}`);

        if (isMounted) {
          setStatus("ready");
          navigate(`/competition/${savedCompetitionUuid}/teams`, { replace: true });
        }
      } catch {
        window.localStorage.removeItem(selectedCompetitionUuidStorageKey);

        if (isMounted) {
          setStatus("invalid");
          navigate("/competitions", { replace: true });
        }
      }
    };

    redirectToSavedCompetition();

    return () => {
      isMounted = false;
    };
  }, [navigate]);

  if (status === "checking") {
    return <Typography color="text.secondary">Loading saved competition...</Typography>;
  }

  return null;
}

export default function App() {
  return (
    <Box
      sx={{
        minHeight: "100vh",
        bgcolor: "background.default"
      }}
    >
      <Header />

      <Container sx={{ py: 4 }}>
        <Routes>
          <Route path="/" element={<SavedCompetitionRedirect />} />
          <Route path="/competitions" element={<CompetitionList />} />
          <Route path="/competition" element={<SavedCompetitionRedirect />} />
          <Route path="/competition/" element={<SavedCompetitionRedirect />} />
          <Route
            path="/competition/:competitionUuid"
            element={<Navigate to="teams" replace />}
          />
          <Route path="/competition/:competitionUuid/teams" element={<Teams />} />
          <Route path="/competition/:competitionUuid/plan" element={<Plan />} />
          <Route path="/competition/:competitionUuid/live" element={<Live />} />
          <Route path="/competition/*" element={<Navigate to="/competitions" replace />} />
        </Routes>
      </Container>

      <Footer />
    </Box>
  );
}
