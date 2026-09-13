export const ROAD_NAMES = {
  ROAD_001: "Noida",
  ROAD_002: "Delhi",
  ROAD_003: "Ghaziabad",
  ROAD_004: "Faridabad",
};

export function getRoadName(roadId, backendName = "") {
  return ROAD_NAMES[roadId] || backendName || roadId || "Unknown road";
}