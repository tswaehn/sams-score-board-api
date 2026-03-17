import { Navigate, Route, Routes } from "react-router-dom";
import { Box, Container } from "@mui/material";
import Teams from "./pages/Teams.jsx";
import Plan from "./pages/Plan.jsx";
import Live from "./pages/Live.jsx";
import CompetitionList from "./pages/CompetitionList.jsx";
import Header from "./components/header.jsx";
import Footer from "./components/footer.jsx";

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
          <Route path="/" element={<CompetitionList />} />
          <Route path="/competitions" element={<CompetitionList />} />
          <Route path="/competition" element={<Navigate to="/competitions" replace />} />
          <Route path="/competition/" element={<Navigate to="/competitions" replace />} />
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
