import { useEffect, useState } from "react";
import { api } from "../api";

export default function History() {
  const [zones, setZones] = useState([]);
  const [roadsById, setRoadsById] = useState({});

  useEffect(() => {
    api.listChronicZones().then(setZones);
    api.listRoads().then((roads) => {
      const map = {};
      roads.forEach((r) => (map[r.id] = r));
      setRoadsById(map);
    });
  }, []);

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-800 mb-4">History / Chronic Problem Zones</h2>

      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-slate-600">
            <tr>
              <th className="text-left px-3 py-2">Road</th>
              <th className="text-left px-3 py-2">Dominant Cause</th>
              <th className="text-left px-3 py-2">Occurrences</th>
              <th className="text-left px-3 py-2">Severity Score</th>
              <th className="text-left px-3 py-2">Notes</th>
            </tr>
          </thead>
          <tbody>
            {zones.map((z) => (
              <tr key={z.id} className="border-t border-slate-100">
                <td className="px-3 py-2 font-medium">{roadsById[z.road_id]?.name || z.road_id}</td>
                <td className="px-3 py-2">{z.dominant_cause}</td>
                <td className="px-3 py-2">{z.occurrence_count}</td>
                <td className="px-3 py-2">{z.severity_score}/100</td>
                <td className="px-3 py-2 text-slate-500">{z.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {zones.length === 0 && (
          <p className="text-slate-500 text-sm p-4">
            No chronic zones flagged yet. Run Person 4's recurrence script once enough
            historical windows have been collected per road.
          </p>
        )}
      </div>
    </div>
  );
}
