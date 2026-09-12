import { NavLink, Routes, Route, Navigate } from "react-router-dom";
import LiveMonitoring from "./pages/LiveMonitoring";
import ProblemAnalysis from "./pages/ProblemAnalysis";
import History from "./pages/History";
import Recommendations from "./pages/Recommendations";
import GISMap from "./pages/GISMap";

const NAV_ITEMS = [
  { to: "/live", label: "Live Monitoring" },
  { to: "/analysis", label: "Problem Analysis" },
  { to: "/history", label: "History / Chronic Zones" },
  { to: "/recommendations", label: "Recommendations" },
  { to: "/map", label: "GIS Map" },
];

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold tracking-wide">
          LaneLogic <span className="text-slate-400 font-normal">| SIH 2026</span>
        </h1>
        <nav className="flex gap-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive ? "bg-slate-700 text-white" : "text-slate-300 hover:bg-slate-800"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="flex-1 p-6">
        <Routes>
          <Route path="/" element={<Navigate to="/live" replace />} />
          <Route path="/live" element={<LiveMonitoring />} />
          <Route path="/analysis" element={<ProblemAnalysis />} />
          <Route path="/history" element={<History />} />
          <Route path="/recommendations" element={<Recommendations />} />
          <Route path="/map" element={<GISMap />} />
        </Routes>
      </main>
    </div>
  );
}
