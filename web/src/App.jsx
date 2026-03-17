import { Route, Routes, useLocation, useNavigate } from "react-router-dom";
import {
  AppBar,
  Box,
  Container,
  Tab,
  Tabs,
  Toolbar,
  Typography
} from "@mui/material";
import Teams from "./pages/Teams.jsx";
import Plan from "./pages/Plan.jsx";
import Live from "./pages/Live.jsx";
import CompetitionList from "./pages/CompetitionList.jsx";
import Footer from "./components/footer.jsx";

const navItems = [
  { path: "/teams", label: "Teams" },
  { path: "/plan", label: "Plan" },
  { path: "/live", label: "Live" }
];

function NavTabs() {
  const location = useLocation();
  const navigate = useNavigate();
  const current =
    navItems.find((item) => location.pathname.startsWith(item.path))?.path ??
    "/teams";

  return (
    <Tabs
      value={current}
      onChange={(_, value) => navigate(value)}
      textColor="inherit"
      indicatorColor="secondary"
      aria-label="Main navigation"
    >
      {navItems.map((item) => (
        <Tab key={item.path} label={item.label} value={item.path} />
      ))}
    </Tabs>
  );
}

export default function App() {
  return (
    <Box
      sx={{
        minHeight: "100vh",
        bgcolor: "background.default"
      }}
    >
      <AppBar
        position="sticky"
        elevation={0}
        sx={{
          background: "rgba(255, 255, 255, 0.95)",
          color: "primary.main",
          borderBottom: "1px solid rgba(20, 17, 15, 0.08)",
          backdropFilter: "blur(12px)"
        }}
      >
        <Toolbar sx={{ py: 1.5, display: "flex", gap: 3 }}>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700 }}>
              DM U16 Dresden 2026
            </Typography>
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              Teams, Plan, Live
            </Typography>
          </Box>
          <Box sx={{ flex: 1 }} />
          <NavTabs />
        </Toolbar>
      </AppBar>

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
