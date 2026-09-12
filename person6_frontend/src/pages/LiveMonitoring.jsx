import { useEffect, useState } from "react";
import { api } from "../api";

const STATUS_STYLES = {
  normal: "bg-green-100 text-green-800",
  moderate: "bg-yellow-100 text-yellow-800",
  severe: "bg-red-100 text-red-800",
};

export default function LiveMonitoring() {
  const [roads, setRoads] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    load();
    const interval = setInterval(load, 8000);
    return () => clearInterval(interval);
  }, []);

  async function load() {
    try {
      const data = await api.listRoads();
      setRoads(data);
      setError(null);
    } catch (err) {
      setError("Could not reach the LaneLogic backend. Is Person 3's API running on :8000?");
    }
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-800 mb-4">Live Monitoring</h2>
      {error && <p className="text-red-600 text-sm mb-4">{error}</p>}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {roads.map((road) => (
          <div key={road.id} className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-medium text-slate-800">{road.name}</h3>
              <span
                className={`text-xs font-semibold px-2 py-1 rounded-full ${STATUS_STYLES[road.current_status]}`}
              >
                {road.current_status}
              </span>
            </div>
            <p className="text-sm text-slate-600">Occupancy: {road.current_occupancy_pct}%</p>
            <p className="text-sm text-slate-600">
              Dominant cause: {road.current_dominant_cause || "n/a"}
            </p>
            {road.is_chronic ? (
              <p className="text-xs text-red-500 mt-1 font-medium">Chronic problem zone</p>
            ) : null}
          </div>
        ))}
        {!error && roads.length === 0 && (
          <p className="text-slate-500 text-sm">
            No roads registered yet. Run Person 5's seed_roads.py, then feed Person 1 → Person 2
            data into the backend.
          </p>
        )}
      </div>
    </div>
  );
}
