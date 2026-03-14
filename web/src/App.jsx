import { NavLink, Route, Routes } from "react-router-dom";
import Teams from "./pages/Teams.jsx";
import Plan from "./pages/Plan.jsx";
import Live from "./pages/Live.jsx";
import "./App.css";

const navItems = [
  { path: "/teams", label: "Teams" },
  { path: "/plan", label: "Plan" },
  { path: "/live", label: "Live" }
];

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">S</span>
          <div>
            <div className="brand-title">DM U16 Dresden</div>
            <div className="brand-subtitle">Teams, Plan, Live</div>
          </div>
        </div>
        <nav className="app-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                isActive ? "nav-link nav-link-active" : "nav-link"
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="app-main">
        <Routes>
          <Route path="/" element={<Teams />} />
          <Route path="/teams" element={<Teams />} />
          <Route path="/plan" element={<Plan />} />
          <Route path="/live" element={<Live />} />
        </Routes>
      </main>
    </div>
  );
}
