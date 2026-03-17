import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { AppBar, Box, Tab, Tabs, Toolbar, Typography } from "@mui/material";
import { fetchJson } from "../api/index.js";

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

export default function Header() {
  const [headerTitle, setHeaderTitle] = useState({
    name: "Competition",
    shortname: ""
  });

  useEffect(() => {
    let isMounted = true;

    const readHeaderTitle = async () => {
      const competitionUuid =
        window.localStorage.getItem("competition-uuid") ?? "";

      if (!competitionUuid) {
        if (isMounted) {
          setHeaderTitle({ name: "Competition", shortname: "" });
        }
        return;
      }

      try {
        const selectedCompetition = await fetchJson(
          `/api/competition/${competitionUuid}`
        );
        const competition =
          selectedCompetition?.competition ?? selectedCompetition ?? null;

        if (isMounted) {
          setHeaderTitle(
            competition
              ? {
                  name: competition.name ?? "Competition",
                  shortname: competition.shortname ?? ""
                }
              : { name: "Competition", shortname: "" }
          );
        }
      } catch {
        if (isMounted) {
          setHeaderTitle({ name: "Competition", shortname: "" });
        }
      }
    };

    readHeaderTitle();
    window.addEventListener("storage", readHeaderTitle);
    window.addEventListener("competition-uuid-updated", readHeaderTitle);

    return () => {
      isMounted = false;
      window.removeEventListener("storage", readHeaderTitle);
      window.removeEventListener("competition-uuid-updated", readHeaderTitle);
    };
  }, []);

  return (
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
          <Typography
            variant="h6"
            sx={{ fontWeight: 700, display: "flex", flexWrap: "wrap", columnGap: 0.75 }}
          >
            <Box component="span" sx={{ whiteSpace: "nowrap" }}>
              {headerTitle.name}
            </Box>
            {headerTitle.shortname && (
              <Box component="span" sx={{ whiteSpace: "nowrap" }}>
                [{headerTitle.shortname}]
              </Box>
            )}
          </Typography>
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            Teams, Plan, Live
          </Typography>
        </Box>
        <Box sx={{ flex: 1 }} />
        <NavTabs />
      </Toolbar>
    </AppBar>
  );
}
