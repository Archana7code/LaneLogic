import MapView from "../MapView";
import "leaflet/dist/leaflet.css";

export default function GISMap() {
  return (
    <div className="h-[calc(100vh-160px)] flex flex-col">
      <div className="flex-1 min-h-0 rounded-md overflow-hidden border border-slate-200 shadow-panel">
        <MapView apiBase="http://localhost:8000" />
      </div>
    </div>
  );
}
