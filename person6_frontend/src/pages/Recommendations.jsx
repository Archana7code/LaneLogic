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
      <h2 className="text-xl font-semibold text-slate-800 mb-4">Recommendations / Interventions</h2>
      <p className="text-xs text-slate-500 mb-4">
        Ranked by expected recovered road space vs. implementation difficulty. These are
        rule-based suggestions, not a guarantee of real-world outcomes.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {recs.map((r) => (
          <div key={r.id} className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="flex justify-between items-start mb-2">
              <h3 className="font-medium text-slate-800">{roadsById[r.road_id]?.name || r.road_id}</h3>
              <span className="text-xs font-semibold bg-slate-100 text-slate-700 px-2 py-1 rounded-full">
                #{r.priority_rank}
              </span>
            </div>
            <p className="text-sm text-slate-800 font-medium">{r.intervention}</p>
            <p className="text-xs text-slate-500 mb-2">Cause: {r.cause}</p>
            <div className="flex gap-4 text-xs text-slate-600">
              <span>Expected benefit: {r.expected_benefit_score}/100</span>
              <span>Difficulty: {r.implementation_difficulty_score}/100</span>
            </div>
            <p className="text-xs text-slate-500 mt-2">{r.rationale}</p>
          </div>
        ))}
        {recs.length === 0 && (
          <p className="text-slate-500 text-sm">No recommendations generated yet.</p>
        )}
      </div>
    </div>
  );
}
