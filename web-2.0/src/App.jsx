import { useEffect, useState } from "react";
import MenuIcon from "@mui/icons-material/Menu";
import SportsVolleyballIcon from "@mui/icons-material/SportsVolleyball";
import { AppBar, Box, Button, Container, Menu, MenuItem, Stack, Toolbar, Typography } from "@mui/material";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { apiPath } from "./api.js";
import SelectionPage from "./pages/SelectionPage.jsx";
import TeamsPage from "./pages/TeamsPage.jsx";
import PlanPage from "./pages/PlanPage.jsx";

function readFocus() { try { const saved = JSON.parse(window.localStorage.getItem("sams-score-board:focus")); return saved?.type && saved?.uuid ? saved : null; } catch { return null; } }

export default function App() {
  const location = useLocation(), navigate = useNavigate();
  const [anchor, setAnchor] = useState(null), [focus, setFocus] = useState(readFocus);
  const entityRoute = location.pathname.match(/^\/(competition|league)\/([^/]+)\/(teams|plan)$/), selectionRoute = location.pathname.match(/^\/select\/(competition|league)$/);
  const routeFocus = entityRoute ? { type: entityRoute[1], uuid: entityRoute[2], name: focus?.type === entityRoute[1] && focus?.uuid === entityRoute[2] ? focus.name : "" } : focus;
  const view = entityRoute?.[3] || "selector", title = selectionRoute || !entityRoute ? "Selection in progress" : routeFocus?.name || "SAMS Score Board";
  const selectType = (type) => { navigate(`/select/${type}`); setAnchor(null); };
  const applyFocus = (nextFocus) => { setFocus(nextFocus); navigate(`/${nextFocus.type}/${nextFocus.uuid}/teams`); };
  useEffect(() => { if (entityRoute && (focus?.type !== entityRoute[1] || focus?.uuid !== entityRoute[2])) setFocus({ type: entityRoute[1], uuid: entityRoute[2], name: "" }); }, [entityRoute, focus]);
  useEffect(() => { if (!routeFocus || routeFocus.name) return undefined; let active = true; fetch(apiPath(`/api/${routeFocus.type}/${routeFocus.uuid}`)).then((r) => r.ok ? r.json() : null).then((entity) => { const name = entity?.name || entity?.shortname || entity?.shortName; if (active && name) { const nextFocus = { ...routeFocus, name }; window.localStorage.setItem("sams-score-board:focus", JSON.stringify(nextFocus)); setFocus(nextFocus); } }).catch(() => {}); return () => { active = false; }; }, [routeFocus]);
  return <Box minHeight="100vh" display="flex" flexDirection="column"><AppBar position="sticky" elevation={0}><Toolbar><Button color="inherit" onClick={(e) => setAnchor(e.currentTarget)} sx={{ minWidth: 0, mr: 1 }} aria-label="Open selection menu"><MenuIcon /></Button><SportsVolleyballIcon sx={{ mr: 1.25 }} /><Typography variant="h6" noWrap>{title}</Typography><Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}><MenuItem selected={selectionRoute?.[1] === "competition"} onClick={() => selectType("competition")}>Select a competition</MenuItem><MenuItem selected={selectionRoute?.[1] === "league"} onClick={() => selectType("league")}>Select a league</MenuItem></Menu>{routeFocus && entityRoute && <Stack direction="row" spacing={0.5} sx={{ ml: "auto" }}><Button color="inherit" onClick={() => navigate(`/${routeFocus.type}/${routeFocus.uuid}/teams`)} sx={{ bgcolor: view === "teams" ? "rgba(255,255,255,.18)" : "transparent" }}>Team</Button><Button color="inherit" onClick={() => navigate(`/${routeFocus.type}/${routeFocus.uuid}/plan`)} sx={{ bgcolor: view === "plan" ? "rgba(255,255,255,.18)" : "transparent" }}>Plan</Button></Stack>}</Toolbar></AppBar><Container maxWidth="lg" sx={{ py: { xs: 3, md: 5 }, flexGrow: 1 }}><Routes><Route path="/" element={<Navigate to="/select/competition" replace />} /><Route path="/select/competition" element={<SelectionPage type="competition" onFocus={applyFocus} />} /><Route path="/select/league" element={<SelectionPage type="league" onFocus={applyFocus} />} /><Route path="/competition/:uuid/teams" element={<TeamsPage focus={routeFocus} />} /><Route path="/league/:uuid/teams" element={<TeamsPage focus={routeFocus} />} /><Route path="/competition/:uuid/plan" element={<PlanPage focus={routeFocus} />} /><Route path="/league/:uuid/plan" element={<PlanPage focus={routeFocus} />} /><Route path="*" element={<Navigate to="/select/competition" replace />} /></Routes></Container><Box component="footer" sx={{ borderTop: 1, borderColor: "divider", bgcolor: "background.paper", py: 2 }}><Container maxWidth="lg"><Typography variant="body2" color="text.secondary">Focus: {routeFocus ? `${routeFocus.type} · ${routeFocus.uuid}` : "No competition or league selected"}</Typography></Container></Box></Box>;
}
