import { NavLink, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Activity, LineChart, History as HistoryIcon, Lightbulb, MapPinned, TrafficCone } from "lucide-react";
import LiveMonitoring from "./pages/LiveMonitoring";
import ProblemAnalysis from "./pages/ProblemAnalysis";
import History from "./pages/History";
import Recommendations from "./pages/Recommendations";
import GISMap from "./pages/GISMap";
import LiveClock from "./components/LiveClock";

const NAV_ITEMS = [
  { to: "/live", label: "Live Monitoring", icon: Activity },
  { to: "/analysis", label: "Problem Analysis", icon: LineChart },
  { to: "/history", label: "History / Chronic Zones", icon: HistoryIcon },
  { to: "/recommendations", label: "Recommendations", icon: Lightbulb },
  { to: "/map", label: "GIS Map", icon: MapPinned },
];

const PAGE_META = {
  "/live": ["Live Monitoring", "Real-time occupancy across every registered road"],
  "/analysis": ["Problem Analysis", "Occupancy trends and cause breakdown per road"],
  "/history": ["History / Chronic Zones", "Roads flagged for repeated congestion"],
  "/recommendations": ["Recommendations", "Ranked interventions by expected impact"],
  "/map": ["GIS Map", "Spatial view of every monitored corridor"],
};

export default function App() {
  const location = useLocation();
  const [title, subtitle] = PAGE_META[location.pathname] || PAGE_META["/live"];

  return (
    <div className="min-h-screen flex bg-slate-50">
      {/* ---------------- Sidebar / ops rail ---------------- */}
      <aside className="w-64 shrink-0 bg-ink-950 text-slate-300 flex flex-col ops-rail">
        <div className="px-5 py-5 flex items-center gap-2.5 border-b border-white/5">
          <div className="h-8 w-8 rounded-md bg-signal-amber/15 flex items-center justify-center">
            <TrafficCone size={18} className="text-signal-amber" />
          </div>
          <div>
            <div className="text-white font-semibold tracking-tight leading-none">LaneLogic</div>
            <div className="text-[10px] text-slate-500 mt-1 tracking-wide">SIH 2026 · TRAFFIC OPS</div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors border-l-2 ${
                    isActive
                      ? "bg-white/5 text-white border-signal-amber"
                      : "text-slate-400 border-transparent hover:bg-white/5 hover:text-slate-200"
                  }`
                }
              >
                <Icon size={16} strokeWidth={2} />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="px-5 py-4 border-t border-white/5 text-[11px] text-slate-500 space-y-1.5">
          <div className="uppercase tracking-wide text-slate-600 mb-2">Status legend</div>
          <LegendRow color="bg-signal-green" label="Normal" />
          <LegendRow color="bg-signal-yellow" label="Moderate" />
          <LegendRow color="bg-signal-red" label="Severe" />
        </div>
      </aside>

      {/* ---------------- Main column ---------------- */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 shrink-0 bg-white border-b border-slate-200 px-8 flex items-center justify-between">
          <div>
            <h1 className="text-base font-semibold text-slate-900 leading-none">{title}</h1>
            <p className="text-xs text-slate-400 mt-1">{subtitle}</p>
          </div>
          <LiveClock />
        </header>

        <main className="flex-1 p-8 overflow-auto">
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
    </div>
  );
}

function LegendRow({ color, label }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`h-1.5 w-1.5 rounded-full ${color}`} />
      {label}
    </div>
  );
}
