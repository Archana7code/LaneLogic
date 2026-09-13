import { useEffect, useState } from "react";
import { api } from "../api";

export default function Recommendations() {
  const [recs, setRecs] = useState([]);
  const [roadsById, setRoadsById] = useState({});

  useEffect(() => {
    api.listRecommendations().then(setRecs);
    api.listRoads().then((roads) => {
      const map = {};
      roads.forEach((r) => (map[r.id] = r));
      setRoadsById(map);
    });
  }, []);

  return (
    <div>
      <p className="text-xs text-slate-400 mb-5 max-w-2xl">
        Ranked by expected recovered road space vs. implementation difficulty. These are rule-based suggestions, not
        a guarantee of real-world outcomes.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {recs.map((r) => (
          <div key={r.id} className="bg-white border border-slate-200 rounded-md p-4 shadow-panel">
            <div className="flex justify-between items-start mb-2">
              <h3 className="font-medium text-slate-800">{roadsById[r.road_id]?.name || r.road_id}</h3>
              <span className="font-mono text-xs font-semibold bg-ink-950 text-signal-amber px-2 py-1 rounded">
                #{r.priority_rank}
              </span>
            </div>

            <p className="text-sm text-slate-800 font-medium mb-1">{r.intervention}</p>
            <p className="text-xs text-slate-400 mb-3">Cause: {r.cause}</p>

            <div className="space-y-2 mb-3">
              <ScoreBar label="Expected benefit" value={r.expected_benefit_score} color="bg-signal-green" />
              <ScoreBar label="Difficulty" value={r.implementation_difficulty_score} color="bg-signal-orange" />
            </div>

            <p className="text-xs text-slate-500 border-t border-slate-100 pt-2">{r.rationale}</p>
          </div>
        ))}

        {recs.length === 0 && (
          <div className="col-span-full text-center py-14 border border-dashed border-slate-300 rounded-md">
            <p className="text-slate-500 text-sm">No recommendations generated yet.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function ScoreBar({ label, value, color }) {
  const pct = Math.min(Math.max(value || 0, 0), 100);
  return (
    <div>
      <div className="flex justify-between text-[11px] text-slate-400 mb-1">
        <span>{label}</span>
        <span className="font-mono text-slate-600">{value}/100</span>
      </div>
      <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
