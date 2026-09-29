import { NavLink, Routes, Route, Navigate, Link, useLocation } from "react-router-dom";
import { Radio, Map as MapIcon, Brain, Target, Bell, Download } from "lucide-react";
import { DataProvider, useData } from "./data";
import LiveMonitoring from "./pages/LiveMonitoring";
import GISMap from "./pages/GISMap";
import ProblemAnalysis from "./pages/ProblemAnalysis";
import Intervention from "./pages/Intervention";
import LiveClock from "./components/LiveClock";
import { Btn } from "./components/ui";

const NAV = [
  { to: "/live", label: "Live Monitoring", icon: Radio },
  { to: "/map", label: "Road Intelligence Map", icon: MapIcon },
  { to: "/analysis", label: "Problem Analysis", icon: Brain },
  { to: "/intervention", label: "Intervention & Closed-Loop", icon: Target },
];
const TITLES = {
  "/live": "Live Road Monitoring & Detection",
  "/map": "Road Intelligence Map & Chronic Zones",
  "/analysis": "Problem Analysis & Explainability",
  "/intervention": "Intervention Engine & Impact Measurement",
};

function exportCsv(events) {
  const cols = ["event_id", "road_id", "camera_id", "vehicle_type", "duration_sec", "road_space_loss_pct", "cause", "cause_confidence", "severity", "status"];
  const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const csv = [cols.join(","), ...events.map((e) => cols.map((c) => esc(e[c])).join(","))].join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  a.download = "lanelogic_obstruction_events.csv";
  a.click();
}

function Shell() {
  const { pathname } = useLocation();
  const { roads, events, alerts, zones, online } = useData();
  const open = alerts.filter((a) => a.status !== "acknowledged").length;
  const tel = [
    ["Monitored corridors", roads.length],
    ["Active checkpoints", zones.length],
    ["Open alerts", open],
    ["Logged events", events.length],
  ];

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      <aside className="flex shrink-0 flex-col border-b border-ink-600 bg-ink-900/80 lg:min-h-screen lg:w-64 lg:border-b-0 lg:border-r">
        <div className="flex items-center gap-3 px-5 py-5">
          <svg width="30" height="30" viewBox="0 0 28 28" aria-hidden="true">
            <rect width="28" height="28" rx="6" fill="#2DDBA0" />
            <path d="M9.5 5v4M9.5 12v4M9.5 19v4M18.5 5v4M18.5 12v4M18.5 19v4" stroke="#060D1B" strokeWidth="2.4" />
          </svg>
          <div>
            <div className="text-lg font-extrabold leading-none text-white">LaneLogic</div>
            <div className="eyebrow mt-1">Road recovery</div>
          </div>
        </div>

        <div className="eyebrow px-5 pb-2 pt-1">Core navigation</div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-col lg:pb-0" aria-label="Main">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 whitespace-nowrap rounded-md px-3 py-2.5 text-sm font-bold transition-colors ${
                  isActive ? "bg-mint text-ink-950" : "text-ink-200 hover:bg-ink-700 hover:text-white"
                }`}>
              <Icon size={17} strokeWidth={2.2} /> {label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-6 hidden px-5 lg:block">
          <div className="eyebrow mb-3">Telemetry status</div>
          <dl className="panel divide-y divide-ink-600">
            {tel.map(([k, v]) => (
              <div key={k} className="flex items-center justify-between px-3 py-2.5 text-xs">
                <dt className="text-ink-300">{k}</dt>
                <dd className="mono font-bold text-mint">{v}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="mt-auto hidden px-5 py-5 lg:block">
          <div className="panel flex items-center gap-2 px-3 py-2.5 text-xs text-ink-200">
            <span className="h-2 w-2 rounded-full pulse-dot" style={{ background: online === false ? "#F0525D" : "#2DDBA0" }} />
            {online === false ? "Backend offline" : online ? "Backend connected" : "Connecting..."}
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-ink-600 bg-ink-900/60 px-6 py-4 lg:px-8">
          <h1 className="text-lg font-extrabold text-white lg:text-xl">{TITLES[pathname] || TITLES["/live"]}</h1>
          <div className="flex items-center gap-3">
            <span className="mono hidden items-center gap-2 rounded-md border border-ink-500 px-3 py-2 text-[11px] text-ink-200 md:inline-flex">
              <span className="h-2 w-2 rounded-full pulse-dot" style={{ background: online === false ? "#F0525D" : "#2DDBA0" }} />
              {online === false ? "API OFFLINE" : `API ONLINE · ${roads.length} CORRIDORS`}
            </span>
            <Btn variant="ghost" onClick={() => exportCsv(events)} disabled={!events.length}><Download size={15} /> Export events</Btn>
            <Link to="/live" aria-label={`${open} open alerts`} className="relative rounded-md border border-ink-500 p-2 text-ink-100 hover:bg-ink-600">
              <Bell size={17} />
              {open > 0 && <span className="mono absolute -right-1.5 -top-1.5 rounded-full bg-[#F0525D] px-1.5 text-[10px] font-bold text-white">{open}</span>}
            </Link>
            <LiveClock />
          </div>
        </header>

        <main className="flex-1 px-6 py-6 lg:px-8">
          <Routes>
            <Route path="/" element={<Navigate to="/live" replace />} />
            <Route path="/live" element={<LiveMonitoring />} />
            <Route path="/map" element={<GISMap />} />
            <Route path="/analysis" element={<ProblemAnalysis />} />
            <Route path="/intervention" element={<Intervention />} />
            <Route path="/history" element={<Navigate to="/map" replace />} />
            <Route path="/recommendations" element={<Navigate to="/intervention" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <DataProvider>
      <Shell />
    </DataProvider>
  );
}
