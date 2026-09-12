// // /*
// //  * LaneLogic - PERSON 5: GIS/Mapping
// //  * ====================================
// //  * MapView.jsx - Leaflet + free OpenStreetMap tiles (no paid Google Maps API).
// //  *
// //  * Renders every road as a colored marker/polygon:
// //  *   GREEN  = normal
// //  *   YELLOW = moderate
// //  *   RED    = severe/chronic
// //  *
// //  * Clicking a road fetches full detail from Person 3's backend
// //  * (GET /roads/{road_id}) and shows blockage %, cause, occurrence
// //  * frequency (if chronic) and the top recommendation in a popup panel.
// //  *
// //  * This component is consumed by PERSON 6 on the "GIS Map" dashboard page:
// //  *   import MapView from "../../person5_gis/MapView";
// //  */

// // import { useEffect, useState } from "react";
// // import { MapContainer, TileLayer, Polygon, Marker, Popup } from "react-leaflet";
// // import "leaflet/dist/leaflet.css";

// // const STATUS_COLOR = {
// //   normal: "#22c55e",   // green
// //   moderate: "#eab308", // yellow
// //   severe: "#ef4444",   // red
// // };

// // const DEFAULT_CENTER = [28.6139, 77.2090]; // Delhi demo center
// // const DEFAULT_ZOOM = 15;

// // function polygonLatLngs(polygonGeojson) {
// //   if (!polygonGeojson || polygonGeojson.type !== "Polygon") return null;
// //   // GeoJSON is [lng, lat]; Leaflet wants [lat, lng].
// //   return polygonGeojson.coordinates[0].map(([lng, lat]) => [lat, lng]);
// // }

// // export default function MapView({ apiBase = "http://localhost:8000" }) {
// //   const [roads, setRoads] = useState([]);
// //   const [selectedDetail, setSelectedDetail] = useState(null);
// //   const [loading, setLoading] = useState(true);

// //   useEffect(() => {
// //     fetchRoads();
// //     const interval = setInterval(fetchRoads, 15000); // light live refresh
// //     return () => clearInterval(interval);
// //   }, []);

// //   async function fetchRoads() {
// //     try {
// //       const res = await fetch(`${apiBase}/roads`);
// //       const data = await res.json();
// //       setRoads(data);
// //     } catch (err) {
// //       console.error("LaneLogic MapView: failed to fetch roads", err);
// //     } finally {
// //       setLoading(false);
// //     }
// //   }

// //   async function handleSelectRoad(roadId) {
// //     try {
// //       const res = await fetch(`${apiBase}/roads/${roadId}`);
// //       const data = await res.json();
// //       setSelectedDetail(data);
// //     } catch (err) {
// //       console.error("LaneLogic MapView: failed to fetch road detail", err);
// //     }
// //   }

// //   return (
// //     <div className="w-full h-full flex flex-col md:flex-row gap-3">
// //       <div className="flex-1 min-h-[420px] rounded-lg overflow-hidden border border-slate-200">
// //         <MapContainer center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} style={{ height: "100%", width: "100%" }}>
// //           <TileLayer
// //             attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
// //             url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
// //           />

// //           {roads.map((road) => {
// //             const color = STATUS_COLOR[road.current_status] || STATUS_COLOR.normal;
// //             const latlngs = polygonLatLngs(road.polygon_geojson);

// //             return (
// //               <div key={road.id}>
// //                 {latlngs && (
// //                   <Polygon
// //                     positions={latlngs}
// //                     pathOptions={{ color, fillColor: color, fillOpacity: 0.45, weight: 2 }}
// //                     eventHandlers={{ click: () => handleSelectRoad(road.id) }}
// //                   />
// //                 )}
// //                 <Marker
// //                   position={[road.latitude, road.longitude]}
// //                   eventHandlers={{ click: () => handleSelectRoad(road.id) }}
// //                 >
// //                   <Popup>
// //                     <strong>{road.name}</strong>
// //                     <br />
// //                     Status: {road.current_status}
// //                     {road.is_chronic ? " (chronic problem zone)" : ""}
// //                   </Popup>
// //                 </Marker>
// //               </div>
// //             );
// //           })}
// //         </MapContainer>
// //       </div>

// //       <aside className="w-full md:w-80 shrink-0 bg-white border border-slate-200 rounded-lg p-4">
// //         <h3 className="font-semibold text-slate-800 mb-2">Road Detail</h3>
// //         {loading && <p className="text-sm text-slate-500">Loading roads…</p>}
// //         {!loading && !selectedDetail && (
// //           <p className="text-sm text-slate-500">Click a road on the map to see details.</p>
// //         )}
// //         {selectedDetail && (
// //           <div className="text-sm space-y-2">
// //             <p className="font-medium text-slate-800">{selectedDetail.road.name}</p>
// //             <p>
// //               Status:{" "}
// //               <span
// //                 className="font-semibold"
// //                 style={{ color: STATUS_COLOR[selectedDetail.road.current_status] }}
// //               >
// //                 {selectedDetail.road.current_status}
// //               </span>
// //             </p>
// //             <p>Current occupancy: {selectedDetail.road.current_occupancy_pct}%</p>
// //             <p>Dominant cause: {selectedDetail.road.current_dominant_cause || "n/a"}</p>
// //             {selectedDetail.chronic_zone && (
// //               <p>
// //                 Chronic zone — flagged {selectedDetail.chronic_zone.occurrence_count} time(s),
// //                 severity {selectedDetail.chronic_zone.severity_score}/100
// //               </p>
// //             )}
// //             {selectedDetail.recommendations?.length > 0 && (
// //               <div>
// //                 <p className="font-medium mt-2">Top recommendation:</p>
// //                 <p>{selectedDetail.recommendations[0].intervention}</p>
// //                 <p className="text-slate-500 text-xs">
// //                   {selectedDetail.recommendations[0].rationale}
// //                 </p>
// //               </div>
// //             )}
// //           </div>
// //         )}
// //       </aside>
// //     </div>
// //   );
// // }











// /*
//  * LaneLogic - PERSON 5: GIS/Mapping
//  * ====================================
//  * MapView.jsx - Leaflet + free OpenStreetMap tiles (no paid Google Maps API).
//  *
//  * Renders every road as a colored marker/polygon:
//  *   GREEN  = normal
//  *   YELLOW = moderate
//  *   RED    = severe/chronic
//  *
//  * Clicking a road fetches full detail from Person 3's backend
//  * (GET /roads/{road_id}) and shows blockage %, cause, occurrence
//  * frequency (if chronic) and the top recommendation in a popup panel.
//  *
//  * This component is consumed by PERSON 6 on the "GIS Map" dashboard page:
//  *   import MapView from "../../person5_gis/MapView";
//  */

// import { useEffect, useState } from "react";
// import { MapContainer, TileLayer, Polygon, Marker, Popup } from "react-leaflet";
// import "leaflet/dist/leaflet.css";
// import {Fragment } from "react";

// const STATUS_COLOR = {
//   normal: "#22c55e",   // green
//   moderate: "#eab308", // yellow
//   severe: "#ef4444",   // red
// };

// const DEFAULT_CENTER = [28.6139, 77.2090]; // Delhi demo center
// const DEFAULT_ZOOM = 15;

// function polygonLatLngs(polygonGeojson) {
//   if (!polygonGeojson || polygonGeojson.type !== "Polygon") return null;
//   // GeoJSON is [lng, lat]; Leaflet wants [lat, lng].
//   return polygonGeojson.coordinates[0].map(([lng, lat]) => [lat, lng]);
// }

// export default function MapView({ apiBase = "http://localhost:8000" }) {
//   const [roads, setRoads] = useState([]);
//   const [selectedDetail, setSelectedDetail] = useState(null);
//   const [loading, setLoading] = useState(true);

//   useEffect(() => {
//     fetchRoads();
//     const interval = setInterval(fetchRoads, 15000); // light live refresh
//     return () => clearInterval(interval);
//   }, []);

//   async function fetchRoads() {
//     try {
//       const res = await fetch(`${apiBase}/roads`);
//       const data = await res.json();
//       setRoads(data);
//     } catch (err) {
//       console.error("LaneLogic MapView: failed to fetch roads", err);
//     } finally {
//       setLoading(false);
//     }
//   }

//   async function handleSelectRoad(roadId) {
//     try {
//       const res = await fetch(`${apiBase}/roads/${roadId}`);
//       const data = await res.json();
//       setSelectedDetail(data);
//     } catch (err) {
//       console.error("LaneLogic MapView: failed to fetch road detail", err);
//     }
//   }

//   return (
//     <div className="w-full h-full flex flex-col md:flex-row gap-3">
//       <div className="flex-1 h-[500px] rounded-lg overflow-hidden border border-slate-200">
//         <MapContainer center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} style={{ height: "100%", width: "100%" }}>
//           <TileLayer
//             attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
//             url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
//           />

//           {roads.map((road) => {
//             const color = STATUS_COLOR[road.current_status] || STATUS_COLOR.normal;
//             const latlngs = polygonLatLngs(road.polygon_geojson);

//             return (
//               <Fragment key={road.id}>
//                 {latlngs && (
//                   <Polygon
//                     positions={latlngs}
//                     pathOptions={{ color, fillColor: color, fillOpacity: 0.45, weight: 2 }}
//                     eventHandlers={{ click: () => handleSelectRoad(road.id) }}
//                   />
//                 )}
//                 <Marker
//                   position={[road.latitude, road.longitude]}
//                   eventHandlers={{ click: () => handleSelectRoad(road.id) }}
//                 >
//                   <Popup>
//                     <strong>{road.name}</strong>
//                     <br />
//                     Status: {road.current_status}
//                     {road.is_chronic ? " (chronic problem zone)" : ""}
//                   </Popup>
//                 </Marker>
//               </Fragment>
//             );
//           })}
//         </MapContainer>
//       </div>

//       <aside className="w-full md:w-80 shrink-0 bg-white border border-slate-200 rounded-lg p-4">
//         <h3 className="font-semibold text-slate-800 mb-2">Road Detail</h3>
//         {loading && <p className="text-sm text-slate-500">Loading roads…</p>}
//         {!loading && !selectedDetail && (
//           <p className="text-sm text-slate-500">Click a road on the map to see details.</p>
//         )}
//         {selectedDetail && (
//           <div className="text-sm space-y-2">
//             <p className="font-medium text-slate-800">{selectedDetail.road.name}</p>
//             <p>
//               Status:{" "}
//               <span
//                 className="font-semibold"
//                 style={{ color: STATUS_COLOR[selectedDetail.road.current_status] }}
//               >
//                 {selectedDetail.road.current_status}
//               </span>
//             </p>
//             <p>Current occupancy: {selectedDetail.road.current_occupancy_pct}%</p>
//             <p>Dominant cause: {selectedDetail.road.current_dominant_cause || "n/a"}</p>
//             {selectedDetail.chronic_zone && (
//               <p>
//                 Chronic zone — flagged {selectedDetail.chronic_zone.occurrence_count} time(s),
//                 severity {selectedDetail.chronic_zone.severity_score}/100
//               </p>
//             )}
//             {selectedDetail.recommendations?.length > 0 && (
//               <div>
//                 <p className="font-medium mt-2">Top recommendation:</p>
//                 <p>{selectedDetail.recommendations[0].intervention}</p>
//                 <p className="text-slate-500 text-xs">
//                   {selectedDetail.recommendations[0].rationale}
//                 </p>
//               </div>
//             )}
//           </div>
//         )}
//       </aside>
//     </div>
//   );
// }












import React, { useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Circle,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";


// ============================================================
// BACKEND
// ============================================================

const API_BASE = "http://localhost:8000";


// ============================================================
// ROAD LOCATIONS
// ============================================================
//
// These are demo coordinates for your video locations.
// Change them later if you know the exact road coordinates.
//
// ROAD_001 -> Noida
// ROAD_002 -> Delhi
// ROAD_003 -> Ghaziabad
// ROAD_004 -> Faridabad
//

const ROAD_LOCATIONS = {
  ROAD_001: {
    name: "Noida",
    latitude: 28.5355,
    longitude: 77.3910,
  },

  ROAD_002: {
    name: "Delhi",
    latitude: 28.6139,
    longitude: 77.2090,
  },

  ROAD_003: {
    name: "Ghaziabad",
    latitude: 28.6692,
    longitude: 77.4538,
  },

  ROAD_004: {
    name: "Faridabad",
    latitude: 28.4089,
    longitude: 77.3178,
  },
};


// ============================================================
// DEFAULT CENTER
// ============================================================

const DEFAULT_CENTER = [28.60, 77.30];


// ============================================================
// MAP AUTO-FIT COMPONENT
// ============================================================

function MapUpdater({ roads }) {
  const map = useMap();

  useEffect(() => {
    if (!roads || roads.length === 0) {
      return;
    }

    const validRoads = roads.filter(
      (road) =>
        Number.isFinite(road.latitude) &&
        Number.isFinite(road.longitude) &&
        road.latitude !== 0 &&
        road.longitude !== 0
    );

    if (validRoads.length === 0) {
      return;
    }

    const bounds = L.latLngBounds(
      validRoads.map((road) => [
        road.latitude,
        road.longitude,
      ])
    );

    map.fitBounds(bounds, {
      padding: [50, 50],
    });
  }, [roads, map]);

  return null;
}


// ============================================================
// MARKER ICON
// ============================================================

function createMarkerIcon(priorityLevel) {
  let color = "#22c55e";

  if (priorityLevel === "low") {
    color = "#eab308";
  }

  if (priorityLevel === "moderate") {
    color = "#f97316";
  }

  if (priorityLevel === "high") {
    color = "#ef4444";
  }

  if (priorityLevel === "critical") {
    color = "#991b1b";
  }

  return L.divIcon({
    className: "custom-road-marker",

    html: `
      <div
        style="
          width: 22px;
          height: 22px;
          background: ${color};
          border: 3px solid white;
          border-radius: 50%;
          box-shadow: 0 2px 8px rgba(0,0,0,0.35);
        "
      ></div>
    `,

    iconSize: [22, 22],
    iconAnchor: [11, 11],
    popupAnchor: [0, -12],
  });
}


// ============================================================
// PRIORITY HELPERS
// ============================================================

function getPriorityLevel(road) {
  if (road.current_priority_level) {
    return String(
      road.current_priority_level
    ).toLowerCase();
  }

  const score = Number(
    road.current_priority_score || 0
  );

  if (score >= 4) {
    return "critical";
  }

  if (score >= 3) {
    return "high";
  }

  if (score >= 2) {
    return "moderate";
  }

  if (score >= 1) {
    return "low";
  }

  return "normal";
}


function getPriorityColor(level) {
  switch (level) {
    case "critical":
      return "#991b1b";

    case "high":
      return "#ef4444";

    case "moderate":
      return "#f97316";

    case "low":
      return "#eab308";

    default:
      return "#22c55e";
  }
}


// ============================================================
// MAIN COMPONENT
// ============================================================

export default function MapView() {

  const [roads, setRoads] = useState([]);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");


  // ==========================================================
  // FETCH ROADS
  // ==========================================================

  useEffect(() => {

    async function loadRoads() {

      try {

        setLoading(true);

        setError("");

        const response = await fetch(
          `${API_BASE}/roads`
        );

        if (!response.ok) {
          throw new Error(
            `Backend returned ${response.status}`
          );
        }

        const backendRoads =
          await response.json();


        // ----------------------------------------------------
        // Convert backend road data into map data
        // ----------------------------------------------------

        const mappedRoads =
          backendRoads.map((road) => {

            const location =
              ROAD_LOCATIONS[road.id];


            // If we have predefined location,
            // use it instead of 0,0 from backend.

            const latitude =
              location?.latitude ??
              Number(road.latitude || 0);

            const longitude =
              location?.longitude ??
              Number(road.longitude || 0);

            const name =
              location?.name ??
              road.name ??
              road.id;


            return {
              ...road,

              latitude,
              longitude,

              displayName: name,

              priorityLevel:
                getPriorityLevel(road),
            };
          });


        // ----------------------------------------------------
        // Remove roads without valid coordinates
        // ----------------------------------------------------

        const validRoads =
          mappedRoads.filter(
            (road) =>
              Number.isFinite(road.latitude) &&
              Number.isFinite(road.longitude) &&
              road.latitude !== 0 &&
              road.longitude !== 0
          );


        setRoads(validRoads);

      } catch (err) {

        console.error(
          "Failed to load roads:",
          err
        );

        setError(
          "Could not connect to LaneLogic backend."
        );

      } finally {

        setLoading(false);

      }
    }


    loadRoads();

  }, []);


  // ==========================================================
  // LOADING
  // ==========================================================

  if (loading) {

    return (
      <div className="flex items-center justify-center h-full min-h-[500px]">

        <div className="text-center">

          <div className="text-lg font-semibold">
            Loading map...
          </div>

          <div className="text-sm text-gray-500 mt-1">
            Fetching road data from LaneLogic
          </div>

        </div>

      </div>
    );
  }


  // ==========================================================
  // ERROR
  // ==========================================================

  if (error) {

    return (
      <div className="flex items-center justify-center h-full min-h-[500px]">

        <div className="text-center">

          <div className="text-red-600 font-semibold">
            {error}
          </div>

          <div className="text-sm text-gray-500 mt-2">
            Make sure Person 3 backend is running on
            port 8000.
          </div>

        </div>

      </div>
    );
  }


  // ==========================================================
  // MAP
  // ==========================================================

  return (

    <div className="w-full h-full min-h-[600px] relative">

      <MapContainer
        center={DEFAULT_CENTER}
        zoom={10}
        scrollWheelZoom={true}
        className="w-full h-full"
        style={{
          minHeight: "600px",
          borderRadius: "12px",
        }}
      >

        {/* ==================================================
            OPENSTREETMAP
        ================================================== */}

        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />


        {/* ==================================================
            AUTO FIT ALL ROADS
        ================================================== */}

        <MapUpdater roads={roads} />


        {/* ==================================================
            ROAD MARKERS
        ================================================== */}

        {roads.map((road) => {

          const priority =
            road.priorityLevel;

          const color =
            getPriorityColor(priority);

          const parkedSpace =
            Number(
              road.current_parked_space_pct || 0
            );

          const parkedWidth =
            Number(
              road.current_parked_width_meters || 0
            );

          const cause =
            road.current_cause ||
            "normal";


          return (

            <React.Fragment key={road.id}>

              {/* ------------------------------------------
                  LARGE COLORED CIRCLE
              ------------------------------------------ */}

              <Circle
                center={[
                  road.latitude,
                  road.longitude,
                ]}
                radius={900}
                pathOptions={{
                  color,
                  fillColor: color,
                  fillOpacity: 0.12,
                  weight: 2,
                }}
              />


              {/* ------------------------------------------
                  MARKER
              ------------------------------------------ */}

              <Marker
                position={[
                  road.latitude,
                  road.longitude,
                ]}
                icon={createMarkerIcon(priority)}
              >

                <Popup>

                  <div
                    style={{
                      minWidth: "220px",
                    }}
                  >

                    {/* ROAD NAME */}

                    <h3
                      style={{
                        fontWeight: "700",
                        fontSize: "17px",
                        marginBottom: "4px",
                      }}
                    >
                      {road.displayName}
                    </h3>


                    {/* ROAD ID */}

                    <div
                      style={{
                        fontSize: "12px",
                        color: "#6b7280",
                        marginBottom: "12px",
                      }}
                    >
                      {road.id}
                    </div>


                    {/* PRIORITY */}

                    <div
                      style={{
                        display: "inline-block",
                        padding: "4px 9px",
                        borderRadius: "999px",
                        background: color,
                        color: "white",
                        fontSize: "12px",
                        fontWeight: "600",
                        marginBottom: "12px",
                        textTransform: "uppercase",
                      }}
                    >
                      {priority}
                    </div>


                    {/* DETAILS */}

                    <div
                      style={{
                        fontSize: "13px",
                        lineHeight: "1.8",
                      }}
                    >

                      <div>
                        <strong>
                          Parked space:
                        </strong>{" "}
                        {parkedSpace.toFixed(2)}%
                      </div>


                      <div>
                        <strong>
                          Parked width:
                        </strong>{" "}
                        {parkedWidth.toFixed(2)} m
                      </div>


                      <div>
                        <strong>
                          Cause:
                        </strong>{" "}
                        {cause}
                      </div>


                      <div>
                        <strong>
                          Priority score:
                        </strong>{" "}
                        {road.current_priority_score ??
                          0}
                      </div>

                    </div>


                    {/* LOCATION */}

                    <div
                      style={{
                        marginTop: "10px",
                        paddingTop: "8px",
                        borderTop:
                          "1px solid #e5e7eb",
                        fontSize: "11px",
                        color: "#6b7280",
                      }}
                    >

                      {road.displayName}

                      <br />

                      {road.latitude.toFixed(4)},
                      {" "}
                      {road.longitude.toFixed(4)}

                    </div>

                  </div>

                </Popup>

              </Marker>

            </React.Fragment>

          );
        })}

      </MapContainer>


      {/* ====================================================
          LEGEND
      ==================================================== */}

      <div
        className="absolute bottom-5 left-5 z-[1000] bg-white rounded-xl shadow-lg p-4"
        style={{
          minWidth: "170px",
        }}
      >

        <div
          className="font-semibold text-sm mb-3"
        >
          Road Status
        </div>


        <div className="space-y-2 text-xs">

          <LegendItem
            color="#22c55e"
            label="Normal"
          />

          <LegendItem
            color="#eab308"
            label="Low"
          />

          <LegendItem
            color="#f97316"
            label="Moderate"
          />

          <LegendItem
            color="#ef4444"
            label="High"
          />

          <LegendItem
            color="#991b1b"
            label="Critical"
          />

        </div>

      </div>


      {/* ====================================================
          ROAD COUNT
      ==================================================== */}

      <div
        className="absolute top-5 right-5 z-[1000] bg-white rounded-xl shadow-lg px-4 py-3"
      >

        <div className="text-xs text-gray-500">
          Monitored locations
        </div>

        <div className="text-xl font-bold">
          {roads.length}
        </div>

      </div>

    </div>
  );
}


// ============================================================
// LEGEND ITEM
// ============================================================

function LegendItem({ color, label }) {

  return (

    <div className="flex items-center gap-2">

      <div
        style={{
          width: "12px",
          height: "12px",
          borderRadius: "50%",
          background: color,
        }}
      />

      <span>
        {label}
      </span>

    </div>

  );
}