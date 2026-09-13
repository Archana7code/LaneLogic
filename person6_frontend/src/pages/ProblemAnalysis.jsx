import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, Legend } from "recharts";
import { api } from "../api";

export default function ProblemAnalysis() {
  const [roads, setRoads] = useState([]);
  const [selectedRoadId, setSelectedRoadId] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    api.listRoads().then((data) => {
      setRoads(data);
      if (data.length > 0) setSelectedRoadId(data[0].id);
    });
  }, []);

  useEffect(() => {
    if (!selectedRoadId) return;
    api.roadHistory(selectedRoadId).then(setHistory);
  }, [selectedRoadId]);

  const chartData = history.map((h) => ({
    window: h.window_index,
    occupancy: h.occupancy_pct,
    blocked: h.blocked_pct,
  }));

  const selectedRoad = roads.find((r) => r.id === selectedRoadId);

  return (
    <div>
      <div className="flex items-center gap-3 mb-5">
        <label className="text-xs uppercase tracking-wide text-slate-400">Road</label>
        <select
          className="border border-slate-300 bg-white rounded-md px-3 py-1.5 text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-signal-amber/40 focus:border-signal-amber"
          value={selectedRoadId || ""}
          onChange={(e) => setSelectedRoadId(e.target.value)}
        >
          {roads.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
        {selectedRoad && (
          <span className="text-xs text-slate-400 font-mono">
            current: <span className="text-slate-600">{selectedRoad.current_occupancy_pct}%</span>
          </span>
        )}
      </div>

      <div className="bg-white border border-slate-200 rounded-md p-4 mb-6 shadow-panel" style={{ height: 300 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
            <XAxis
              dataKey="window"
              label={{ value: "Time window", position: "insideBottom", dy: 10, fontSize: 11, fill: "#94a3b8" }}
              tick={{ fontSize: 11, fontFamily: "IBM Plex Mono", fill: "#94a3b8" }}
              axisLine={{ stroke: "#e2e8f0" }}
              tickLine={false}
            />
            <YAxis
              label={{ value: "%", angle: -90, position: "insideLeft", fontSize: 11, fill: "#94a3b8" }}
              tick={{ fontSize: 11, fontFamily: "IBM Plex Mono", fill: "#94a3b8" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                fontFamily: "IBM Plex Mono",
                fontSize: 12,
                borderRadius: 6,
                border: "1px solid #e2e8f0",
              }}
            />
            <Legend wrapperStyle={{ fontSize: 12, fontFamily: "IBM Plex Sans" }} />
            <Line type="monotone" dataKey="occupancy" stroke="#F5A623" strokeWidth={2} dot={false} name="Occupancy %" />
            <Line type="monotone" dataKey="blocked" stroke="#EF4444" strokeWidth={2} dot={false} name="Blocked %" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white border border-slate-200 rounded-md overflow-hidden shadow-panel">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wide sticky top-0">
            <tr>
              <th className="text-left px-3 py-2.5 font-medium">Window</th>
              <th className="text-left px-3 py-2.5 font-medium">Vehicles</th>
              <th className="text-left px-3 py-2.5 font-medium">Occupancy %</th>
              <th className="text-left px-3 py-2.5 font-medium">Blocked %</th>
              <th className="text-left px-3 py-2.5 font-medium">Cause</th>
              <th className="text-left px-3 py-2.5 font-medium">Explanation</th>
            </tr>
          </thead>
          <tbody className="font-mono text-[13px]">
            {history.map((h) => (
              <tr key={h.window_index} className="border-t border-slate-100 hover:bg-slate-50/70">
                <td className="px-3 py-2 text-slate-500">{h.window_index}</td>
                <td className="px-3 py-2 text-slate-700">{h.vehicle_count}</td>
                <td className="px-3 py-2 text-slate-700">{h.occupancy_pct}</td>
                <td className="px-3 py-2 text-slate-700">{h.blocked_pct}</td>
                <td className="px-3 py-2 font-sans text-slate-700">{h.cause}</td>
                <td className="px-3 py-2 font-sans text-slate-500">{h.cause_explanation}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {history.length === 0 && (
          <p className="text-slate-500 text-sm p-4">No analysis windows yet for this road.</p>
        )}
      </div>
    </div>
  );
}
