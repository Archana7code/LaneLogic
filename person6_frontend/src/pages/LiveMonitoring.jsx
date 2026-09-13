import { useEffect, useState } from "react";
import { AlertTriangle, WifiOff } from "lucide-react";
import { api } from "../api";
import StatusDot from "../components/StatusDot";

const BORDER_BY_STATUS = {
  normal: "border-l-signal-green",
  moderate: "border-l-signal-yellow",
  severe: "border-l-signal-red",
};

// Display names for each demo road
const ROAD_NAMES = {
  ROAD_001: "Noida",
  ROAD_002: "Delhi",
  ROAD_003: "Ghaziabad",
  ROAD_004: "Faridabad",
};

export default function LiveMonitoring() {
  const [roads, setRoads] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    load();

    const interval = setInterval(load, 8000);

    return () => clearInterval(interval);
  }, []);

  async function load() {
    try {
      const data = await api.listRoads();

      console.log("Road data received from backend:", data);

      setRoads(data);
      setError(null);
    } catch (err) {
      console.error(err);

      setError(
        "Could not reach the LaneLogic backend. Is Person 3's API running on :8000?"
      );
    } finally {
      setLoading(false);
    }
  }

  const severeCount = roads.filter(
    (road) => road.current_status === "severe"
  ).length;

  const chronicCount = roads.filter(
    (road) => road.is_chronic
  ).length;

  const avgOccupancy = roads.length
    ? Math.round(
        roads.reduce(
          (sum, road) => sum + (road.current_occupancy_pct || 0),
          0
        ) / roads.length
      )
    : 0;

  function getRoadDisplayName(road) {
    const backendRoadId =
      road.road_id ||
      road.roadId ||
      road.name ||
      road.id;

    return (
      ROAD_NAMES[backendRoadId] ||
      road.name ||
      road.road_id ||
      road.roadId ||
      road.id ||
      "Unknown road"
    );
  }

  return (
    <div>
      {error && (
        <div className="mb-6 flex items-start gap-3 bg-red-50 border border-red-200 text-red-700 rounded-md px-4 py-3 text-sm">
          <WifiOff size={16} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ---------------- KPI strip ---------------- */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KpiTile
          label="Roads monitored"
          value={roads.length}
        />

        <KpiTile
          label="Avg. occupancy"
          value={`${avgOccupancy}%`}
        />

        <KpiTile
          label="Severe right now"
          value={severeCount}
          accent={
            severeCount > 0
              ? "text-signal-red"
              : undefined
          }
        />

        <KpiTile
          label="Chronic zones"
          value={chronicCount}
          accent={
            chronicCount > 0
              ? "text-signal-orange"
              : undefined
          }
        />
      </div>

      {/* ---------------- Road cards ---------------- */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading &&
          Array.from({ length: 6 }).map((_, index) => (
            <CardSkeleton key={index} />
          ))}

        {!loading &&
          roads.map((road) => (
            <div
              key={road.id || road.road_id}
              className={`bg-white border border-slate-200 border-l-4 ${
                BORDER_BY_STATUS[road.current_status] ||
                "border-l-slate-300"
              } rounded-md p-4 shadow-panel`}
            >
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-medium text-slate-800">
                  {getRoadDisplayName(road)}
                </h3>

                <StatusDot
                  status={road.current_status}
                  live={road.current_status === "severe"}
                />
              </div>

              <div className="flex items-baseline gap-1 mb-2">
                <span className="font-mono text-2xl font-semibold text-slate-900 tabular-nums">
                  {road.current_occupancy_pct || 0}
                </span>

                <span className="text-xs text-slate-400">
                  % occupancy
                </span>
              </div>

              <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden mb-3">
                <div
                  className={`h-full rounded-full ${
                    road.current_status === "severe"
                      ? "bg-signal-red"
                      : road.current_status === "moderate"
                      ? "bg-signal-yellow"
                      : "bg-signal-green"
                  }`}
                  style={{
                    width: `${Math.min(
                      road.current_occupancy_pct || 0,
                      100
                    )}%`,
                  }}
                />
              </div>

              <p className="text-xs text-slate-500">
                Dominant cause:{" "}
                <span className="text-slate-700 font-medium">
                  {road.current_dominant_cause || "n/a"}
                </span>
              </p>

              {road.is_chronic ? (
                <p className="flex items-center gap-1 text-xs text-signal-orange mt-2 font-medium">
                  <AlertTriangle size={12} />
                  Chronic problem zone
                </p>
              ) : null}
            </div>
          ))}

        {!loading && !error && roads.length === 0 && (
          <div className="col-span-full text-center py-14 border border-dashed border-slate-300 rounded-md">
            <p className="text-slate-500 text-sm">
              No roads registered yet. Feed Person 1 → Person 2 data
              into the backend.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function KpiTile({ label, value, accent }) {
  return (
    <div className="bg-white border border-slate-200 rounded-md px-4 py-3 shadow-panel">
      <div className="text-[11px] uppercase tracking-wide text-slate-400 mb-1">
        {label}
      </div>

      <div
        className={`font-mono text-2xl font-semibold tabular-nums ${
          accent || "text-slate-900"
        }`}
      >
        {value}
      </div>
    </div>
  );
}

function CardSkeleton() {
  return (
    <div className="bg-white border border-slate-200 rounded-md p-4 animate-pulse">
      <div className="flex justify-between mb-3">
        <div className="h-4 w-24 bg-slate-100 rounded" />
        <div className="h-4 w-14 bg-slate-100 rounded" />
      </div>

      <div className="h-6 w-16 bg-slate-100 rounded mb-3" />

      <div className="h-1.5 w-full bg-slate-100 rounded-full mb-3" />

      <div className="h-3 w-32 bg-slate-100 rounded" />
    </div>
  );
}