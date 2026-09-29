/*
 * LaneLogic - PERSON 6: Frontend/Dashboard
 * api.js - single place every page calls Person 3's FastAPI backend.
 * Base URL can be overridden with VITE_API_BASE in person6_frontend/.env
 */
// export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
export const API_BASE = import.meta.env.VITE_API_BASE || "https://lanelogic-backend.onrender.com";

async function request(path, options) {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) throw new Error(`${options?.method || "GET"} ${path} failed: ${res.status}`);
  return res.json();
}
const post = (path, body) =>
  request(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const api = {
  listRoads: () => request("/roads"),
  roadDetail: (id) => request(`/roads/${id}`),
  roadHistory: (id) => request(`/roads/${id}/history`),
  listChronicZones: () => request("/chronic-zones"),
  listRecommendations: (roadId) => request(roadId ? `/recommendations?road_id=${roadId}` : "/recommendations"),
  listAlerts: () => request("/alerts"),
  acknowledgeAlert: (id, by = "traffic_operator") => post(`/alerts/${id}/acknowledge`, { acknowledged_by: by }),
  listEvents: (roadId, limit = 100) => request(`/events?limit=${limit}${roadId ? `&road_id=${roadId}` : ""}`),
  generateRecommendations: (roadId) => post("/recommendations/generate", { road_id: roadId }),
  simulate: (roadId, type) => post("/simulations/intervention", { road_id: roadId, intervention_type: type }),
  sendFeedback: (p) => post("/feedback", p),
  predictCause: (p) => post("/causes/predict", p),
  listOutcomes: () => request("/interventions/outcomes"),
  modelVersions: () => request("/models/versions"),
};
