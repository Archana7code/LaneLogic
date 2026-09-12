// import MapView from "@person5/MapView";

// export default function GISMap() {
//   return (
//     <div className="h-[calc(100vh-140px)]">
//       <h2 className="text-xl font-semibold text-slate-800 mb-4">GIS Map</h2>
//       <MapView apiBase="http://localhost:8000" />
//     </div>
//   );
// }



// import MapView from "@person5/MapView";

// export default function GISMap() {
//   return (
//     <div className="h-[calc(100vh-140px)] flex flex-col">
//       <h2 className="text-xl font-semibold text-slate-800 mb-4 shrink-0">GIS Map</h2>
//       <div className="flex-1 min-h-0">
//         <MapView apiBase="http://localhost:8000" />
//       </div>
//     </div>
//   );
// }

import MapView from "../MapView";
import "leaflet/dist/leaflet.css";

export default function GISMap() {
  return (
    <div className="h-[calc(100vh-140px)] flex flex-col">
      <h2 className="text-xl font-semibold text-slate-800 mb-4 shrink-0">GIS Map</h2>
      <div className="flex-1 min-h-0">
        <MapView apiBase="http://localhost:8000" />
      </div>
    </div>
  );
}