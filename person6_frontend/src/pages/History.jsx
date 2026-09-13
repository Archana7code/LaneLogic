// import { useEffect, useState } from "react";
// import { api } from "../api";

// export default function History() {
//   const [zones, setZones] = useState([]);
//   const [roadsById, setRoadsById] = useState({});

//   useEffect(() => {
//     api.listChronicZones().then(setZones);
//     api.listRoads().then((roads) => {
//       const map = {};
//       roads.forEach((r) => (map[r.id] = r));
//       setRoadsById(map);
//     });
//   }, []);

//   return (
//     <div>
//       <div className="bg-white border border-slate-200 rounded-md overflow-hidden shadow-panel">
//         <table className="w-full text-sm">
//           <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wide">
//             <tr>
//               <th className="text-left px-3 py-2.5 font-medium">Road</th>
//               <th className="text-left px-3 py-2.5 font-medium">Dominant cause</th>
//               <th className="text-left px-3 py-2.5 font-medium">Occurrences</th>
//               <th className="text-left px-3 py-2.5 font-medium w-48">Severity</th>
//               <th className="text-left px-3 py-2.5 font-medium">Notes</th>
//             </tr>
//           </thead>
//           <tbody>
//             {zones.map((z) => (
//               <tr key={z.id} className="border-t border-slate-100 hover:bg-slate-50/70">
//                 <td className="px-3 py-2.5 font-medium text-slate-800">
//                   {roadsById[z.road_id]?.name || z.road_id}
//                 </td>
//                 <td className="px-3 py-2.5 text-slate-600">{z.dominant_cause}</td>
//                 <td className="px-3 py-2.5 font-mono text-slate-700">{z.occurrence_count}</td>
//                 <td className="px-3 py-2.5">
//                   <SeverityBar score={z.severity_score} />
//                 </td>
//                 <td className="px-3 py-2.5 text-slate-500">{z.notes}</td>
//               </tr>
//             ))}
//           </tbody>
//         </table>
//         {zones.length === 0 && (
//           <p className="text-slate-500 text-sm p-4">
//             No chronic zones flagged yet. Run Person 4's recurrence script once enough historical windows have been
//             collected per road.
//           </p>
//         )}
//       </div>
//     </div>
//   );
// }

// function SeverityBar({ score }) {
//   const pct = Math.min(Math.max(score || 0, 0), 100);
//   const color = pct >= 70 ? "bg-signal-red" : pct >= 40 ? "bg-signal-orange" : "bg-signal-yellow";
//   return (
//     <div className="flex items-center gap-2">
//       <div className="h-1.5 w-24 bg-slate-100 rounded-full overflow-hidden">
//         <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
//       </div>
//       <span className="font-mono text-xs text-slate-600 tabular-nums">{score}/100</span>
//     </div>
//   );
// }


import { useEffect, useState } from "react";
import { api } from "../api";
import { getRoadName } from "../utils/roadNames";

export default function History() {
  const [zones, setZones] = useState([]);
  const [roadsById, setRoadsById] = useState({});

  useEffect(() => {
    api.listChronicZones().then(setZones);

    api.listRoads().then((roads) => {
      const map = {};

      roads.forEach((road) => {
        map[road.id] = road;
      });

      setRoadsById(map);
    });
  }, []);

  return (
    <div>
      <div className="bg-white border border-slate-200 rounded-md overflow-hidden shadow-panel">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wide">
              <tr>
                <th className="text-left px-3 py-2.5 font-medium">
                  Road
                </th>
                <th className="text-left px-3 py-2.5 font-medium">
                  Dominant cause
                </th>
                <th className="text-left px-3 py-2.5 font-medium">
                  Occurrences
                </th>
                <th className="text-left px-3 py-2.5 font-medium w-48">
                  Severity
                </th>
                <th className="text-left px-3 py-2.5 font-medium">
                  Notes
                </th>
              </tr>
            </thead>

            <tbody>
              {zones.map((zone) => (
                <tr
                  key={zone.id}
                  className="border-t border-slate-100 hover:bg-slate-50/70"
                >
                  <td className="px-3 py-2.5 font-medium text-slate-800">
                    {getRoadName(
                      zone.road_id,
                      roadsById[zone.road_id]?.name
                    )}
                  </td>

                  <td className="px-3 py-2.5 text-slate-600">
                    {zone.dominant_cause || "unclassified"}
                  </td>

                  <td className="px-3 py-2.5 font-mono text-slate-700">
                    {zone.occurrence_count}
                  </td>

                  <td className="px-3 py-2.5">
                    <SeverityBar score={zone.severity_score} />
                  </td>

                  <td className="px-3 py-2.5 text-slate-500">
                    {zone.notes || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {zones.length === 0 && (
          <p className="text-slate-500 text-sm p-4">
            No chronic zones flagged yet. Run Person 4's recurrence
            script once enough historical windows have been collected
            per road.
          </p>
        )}
      </div>
    </div>
  );
}

function SeverityBar({ score }) {
  const numericScore = Number(score || 0);

  const percentage = Math.min(
    Math.max(numericScore, 0),
    100
  );

  const color =
    percentage >= 70
      ? "bg-signal-red"
      : percentage >= 40
      ? "bg-signal-orange"
      : "bg-signal-yellow";

  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      <span className="font-mono text-xs text-slate-600 tabular-nums">
        {numericScore}/100
      </span>
    </div>
  );
}