import { Route, Routes } from "react-router-dom";
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
          <Route path="/" element={<Teams />} />
          <Route path="/teams" element={<Teams />} />
          <Route path="/competitions" element={<CompetitionList />} />
          <Route path="/plan" element={<Plan />} />
          <Route path="/live" element={<Live />} />
        </Routes>
      </Container>

      <Footer />
    </Box>
  );
}
