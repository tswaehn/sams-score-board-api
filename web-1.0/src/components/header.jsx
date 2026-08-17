import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  AppBar,
  Box,
  Divider,
  IconButton,
  Menu,
  MenuItem,
  Tab,
  Tabs,
  Toolbar,
  Typography
} from "@mui/material";
import { fetchJson, useIsMobile } from "../api/api.js";
import {
  getEntityConfig,
  getEntityFromPath,
  isEmbeddedSearch
} from "../entities/entity.js";

function getNavItems(entityType) {
  return [
    { section: "teams", label: "Teams" },
    { section: "plan", label: "Plan" },
    { section: "live", label: "Live" }
  ];
}

function BurgerButton({
  ariaLabel,
  ariaControls,
  ariaExpanded,
  onClick,
  sx = {},
  disabled = false
}) {
  return (
    <IconButton
      aria-label={ariaLabel}
      aria-controls={ariaControls}
      aria-haspopup="true"
      aria-expanded={ariaExpanded}
      onClick={onClick}
      disabled={disabled}
      sx={{
        width: 48,
        height: 48,
        border: "1px solid rgba(20, 17, 15, 0.14)",
        borderRadius: "50%",
        color: "primary.main",
        ...sx
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
  );
}

function SelectionMenu() {
  const location = useLocation();
  const navigate = useNavigate();
  const [anchorEl, setAnchorEl] = useState(null);
  const { entityType, entityUuid } = getEntityFromPath(location.pathname);
  const searchSuffix = location.search ?? "";
  const current =
    location.pathname.startsWith("/leagues") || location.pathname.startsWith("/league/")
      ? "/leagues"
      : "/competitions";
  const isCompetitionOverviewRoute =
    entityType === "competition" &&
    entityUuid &&
    location.pathname.startsWith(`/competition/${entityUuid}/full-screen`);

  const handleNavigate = (path) => {
    setAnchorEl(null);
    navigate(path);
  };

  return (
    <>
      <BurgerButton
        ariaLabel="Open selection menu"
        ariaControls={anchorEl ? "header-selection-menu" : undefined}
        ariaExpanded={anchorEl ? "true" : undefined}
        onClick={(event) => setAnchorEl(event.currentTarget)}
      />
      <Menu
        id="header-selection-menu"
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
        transformOrigin={{ vertical: "top", horizontal: "left" }}
      >
        <MenuItem selected={current === "/competitions"} onClick={() => handleNavigate("/competitions")}>
          Competition List
        </MenuItem>
        <MenuItem selected={current === "/leagues"} onClick={() => handleNavigate("/leagues")}>
          League List
        </MenuItem>
        {entityType === "competition" && entityUuid && (
          <>
            <Divider />
            <MenuItem
              selected={Boolean(isCompetitionOverviewRoute)}
              onClick={() => handleNavigate(`/competition/${entityUuid}/full-screen${searchSuffix}`)}
            >
              Full Screen
            </MenuItem>
          </>
        )}
      </Menu>
    </>
  );
}

function NavTabs({ entityType }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { entityUuid } = getEntityFromPath(location.pathname);
  const entityConfig = getEntityConfig(entityType);
  const navItems = getNavItems(entityType);
  const searchSuffix = location.search ?? "";
  const current =
    navItems.find((item) =>
      location.pathname.startsWith(`${entityConfig.routeBase}/${entityUuid}/${item.section}`)
    )?.section ?? false;

  return (
    <Tabs
      value={current}
      onChange={(_, value) =>
        navigate(`${entityConfig.routeBase}/${entityUuid}/${value}${searchSuffix}`)
      }
      textColor="inherit"
      indicatorColor="secondary"
      aria-label="Main navigation"
    >
      {navItems.map((item) => (
        <Tab
          key={item.section}
          label={item.label}
          value={item.section}
          disabled={!entityUuid}
        />
      ))}
    </Tabs>
  );
}

function MobileNavMenu({ entityType }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { entityUuid } = getEntityFromPath(location.pathname);
  const entityConfig = getEntityConfig(entityType);
  const navItems = getNavItems(entityType);
  const searchSuffix = location.search ?? "";
  const [anchorEl, setAnchorEl] = useState(null);
  const current =
    navItems.find((item) =>
      location.pathname.startsWith(`${entityConfig.routeBase}/${entityUuid}/${item.section}`)
    )?.section ?? "";

  const handleNavigate = (section) => {
    setAnchorEl(null);
    navigate(`${entityConfig.routeBase}/${entityUuid}/${section}${searchSuffix}`);
  };

  return (
    <>
      <BurgerButton
        ariaLabel="Open navigation menu"
        ariaControls={anchorEl ? "header-mobile-menu" : undefined}
        ariaExpanded={anchorEl ? "true" : undefined}
        onClick={(event) => setAnchorEl(event.currentTarget)}
        disabled={!entityUuid}
      />
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
  const isMobile = useIsMobile();
  const isEmbedded = isEmbeddedSearch(location.search);
  const { entityType, entityUuid } = getEntityFromPath(location.pathname);
  const resolvedEntityType = entityType || "competition";
  const entityConfig = getEntityConfig(resolvedEntityType);
  const [headerTitle, setHeaderTitle] = useState({
    name: entityConfig.singularLabel,
    shortname: ""
  });

  useEffect(() => {
    let isMounted = true;

    const readHeaderTitle = async () => {
      if (!entityType || !entityUuid) {
        if (isMounted) {
          setHeaderTitle({ name: entityConfig.singularLabel, shortname: "" });
        }
        return;
      }

      try {
        const selectedEntity = await fetchJson(`/api/${entityType}/${entityUuid}`);
        const entity = selectedEntity?.competition ?? selectedEntity?.league ?? selectedEntity ?? null;

        if (isMounted) {
          setHeaderTitle(
            entity
              ? {
                  name: entity.name ?? entityConfig.singularLabel,
                  shortname: entity.shortname ?? ""
                }
              : { name: entityConfig.singularLabel, shortname: "" }
          );
        }
      } catch {
        if (isMounted) {
          setHeaderTitle({ name: entityConfig.singularLabel, shortname: "" });
        }
      }
    };

    readHeaderTitle();

    return () => {
      isMounted = false;
    };
  }, [entityConfig.singularLabel, entityType, entityUuid]);

  useEffect(() => {
    document.title = headerTitle.name || entityConfig.singularLabel;
  }, [entityConfig.singularLabel, headerTitle]);

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
        <Box sx={{ flex: "1 1 0", minWidth: 0, display: "flex", alignItems: "flex-start", gap: 1.5 }}>
          {!isEmbedded && <SelectionMenu />}
          <Box sx={{ minWidth: 0 }}>
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
        </Box>
        <Box
          sx={{
            ml: "auto",
            alignSelf: isMobile ? "flex-start" : "center"
          }}
        >
          {isMobile ? (
            <MobileNavMenu entityType={resolvedEntityType} />
          ) : (
            <NavTabs entityType={resolvedEntityType} />
          )}
        </Box>
      </Toolbar>
    </AppBar>
  );
}
