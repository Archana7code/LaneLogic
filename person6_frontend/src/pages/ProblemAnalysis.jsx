import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from "recharts";
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

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-800 mb-4">Problem Analysis</h2>

      <select
        className="border border-slate-300 rounded-md px-3 py-2 text-sm mb-4"
        value={selectedRoadId || ""}
        onChange={(e) => setSelectedRoadId(e.target.value)}
      >
        {roads.map((r) => (
          <option key={r.id} value={r.id}>
            {r.name}
          </option>
        ))}
      </select>

      <div className="bg-white border border-slate-200 rounded-lg p-4 mb-6" style={{ height: 300 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="window" label={{ value: "Time window", position: "insideBottom", dy: 10 }} />
            <YAxis label={{ value: "%", angle: -90, position: "insideLeft" }} />
            <Tooltip />
            <Line type="monotone" dataKey="occupancy" stroke="#3b82f6" name="Occupancy %" />
            <Line type="monotone" dataKey="blocked" stroke="#ef4444" name="Blocked %" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-slate-600">
            <tr>
              <th className="text-left px-3 py-2">Window</th>
              <th className="text-left px-3 py-2">Vehicles</th>
              <th className="text-left px-3 py-2">Occupancy %</th>
              <th className="text-left px-3 py-2">Blocked %</th>
              <th className="text-left px-3 py-2">Cause</th>
              <th className="text-left px-3 py-2">Explanation</th>
            </tr>
          </thead>
          <tbody>
            {history.map((h) => (
              <tr key={h.window_index} className="border-t border-slate-100">
                <td className="px-3 py-2">{h.window_index}</td>
                <td className="px-3 py-2">{h.vehicle_count}</td>
                <td className="px-3 py-2">{h.occupancy_pct}</td>
                <td className="px-3 py-2">{h.blocked_pct}</td>
                <td className="px-3 py-2">{h.cause}</td>
                <td className="px-3 py-2 text-slate-500">{h.cause_explanation}</td>
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
