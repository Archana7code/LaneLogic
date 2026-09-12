/*
 * LaneLogic - PERSON 6: Frontend/Dashboard
 * ============================================
 * api.js - single place all pages call into Person 3's FastAPI backend.
 * No mocked/disconnected data - every page below calls one of these.
 */

export const API_BASE = "http://localhost:8000";

async function getJSON(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

export const api = {
  listRoads: () => getJSON("/roads"),
  roadDetail: (roadId) => getJSON(`/roads/${roadId}`),
  roadHistory: (roadId) => getJSON(`/roads/${roadId}/history`),
  listChronicZones: () => getJSON("/chronic-zones"),
  listRecommendations: (roadId) =>
    getJSON(roadId ? `/recommendations?road_id=${roadId}` : "/recommendations"),
};
