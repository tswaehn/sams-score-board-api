import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  AppBar,
  Box,
  IconButton,
  Menu,
  MenuItem,
  Tab,
  Tabs,
  Toolbar,
  Typography,
  useMediaQuery
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { fetchJson } from "../api/api.js";

const navItems = [
  { section: "teams", label: "Teams" },
  { section: "plan", label: "Plan" },
  { section: "live", label: "Live" }
];

function getCompetitionUuidFromPath(pathname) {
  const match = pathname.match(/^\/competition\/([^/]+)(?:\/|$)/);
  return match?.[1] ?? "";
}

function NavTabs() {
  const location = useLocation();
  const navigate = useNavigate();
  const competitionUuid = getCompetitionUuidFromPath(location.pathname);
  const current =
    navItems.find((item) =>
      location.pathname.startsWith(`/competition/${competitionUuid}/${item.section}`)
    )?.section ?? false;

  return (
    <Tabs
      value={current}
      onChange={(_, value) => navigate(`/competition/${competitionUuid}/${value}`)}
      textColor="inherit"
      indicatorColor="secondary"
      aria-label="Main navigation"
    >
      {navItems.map((item) => (
        <Tab
          key={item.section}
          label={item.label}
          value={item.section}
          disabled={!competitionUuid}
        />
      ))}
    </Tabs>
  );
}

function MobileNavMenu() {
  const location = useLocation();
  const navigate = useNavigate();
  const competitionUuid = getCompetitionUuidFromPath(location.pathname);
  const [anchorEl, setAnchorEl] = useState(null);
  const current =
    navItems.find((item) =>
      location.pathname.startsWith(`/competition/${competitionUuid}/${item.section}`)
    )?.section ?? "";

  const handleNavigate = (section) => {
    setAnchorEl(null);
    navigate(`/competition/${competitionUuid}/${section}`);
  };

  return (
    <>
      <IconButton
        aria-label="Open navigation menu"
        aria-controls={anchorEl ? "header-mobile-menu" : undefined}
        aria-haspopup="true"
        aria-expanded={anchorEl ? "true" : undefined}
        onClick={(event) => setAnchorEl(event.currentTarget)}
        disabled={!competitionUuid}
        sx={{
          width: 48,
          height: 48,
          border: "1px solid rgba(20, 17, 15, 0.14)",
          borderRadius: "50%",
          color: "primary.main"
        }}
      >
        <Box
          component="span"
          sx={{
            display: "inline-flex",
            flexDirection: "column",
            justifyContent: "center",
            gap: 0.5
          }}
        >
          {[0, 1, 2].map((bar) => (
            <Box
              key={bar}
              component="span"
              sx={{
                display: "block",
                width: 18,
                height: 2,
                borderRadius: 999,
                bgcolor: "currentColor"
              }}
            />
          ))}
        </Box>
      </IconButton>
      <Menu
        id="header-mobile-menu"
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
      >
        {navItems.map((item) => (
          <MenuItem
            key={item.section}
            selected={current === item.section}
            onClick={() => handleNavigate(item.section)}
          >
            {item.label}
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}

export default function Header() {
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  const [headerTitle, setHeaderTitle] = useState({
    name: "Competition",
    shortname: ""
  });

  useEffect(() => {
    let isMounted = true;

    const readHeaderTitle = async () => {
      const competitionUuid = getCompetitionUuidFromPath(location.pathname);

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

    return () => {
      isMounted = false;
    };
  }, [location.pathname]);

  useEffect(() => {
    document.title = headerTitle.name || "Competition";
  }, [headerTitle]);

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
      <Toolbar
        sx={{
          py: 1.5,
          display: "flex",
          alignItems: "flex-start",
          gap: 2,
          flexWrap: "wrap"
        }}
      >
        <Box sx={{ flex: "1 1 0", minWidth: 0 }}>
          <Typography
            variant="h6"
            sx={{
              fontWeight: 700,
              lineHeight: 1.15,
              whiteSpace: "normal",
              overflowWrap: "anywhere"
            }}
          >
            <Box component="span">{headerTitle.name}</Box>
            {headerTitle.shortname && (
              <Box component="span" sx={{ display: "block", mt: 0.25 }}>
                [{headerTitle.shortname}]
              </Box>
            )}
          </Typography>
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            Teams, Plan, Live
          </Typography>
        </Box>
        <Box
          sx={{
            ml: "auto",
            alignSelf: isMobile ? "flex-start" : "center"
          }}
        >
          {isMobile ? <MobileNavMenu /> : <NavTabs />}
        </Box>
      </Toolbar>
    </AppBar>
  );
}
