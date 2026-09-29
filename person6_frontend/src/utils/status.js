// Priority levels come from the backend (current_priority_level). "severe" (older API) maps to "high".
export const LEVELS = ["normal", "low", "moderate", "high", "critical"];
export const RANK = { normal: 0, low: 1, moderate: 2, high: 3, critical: 4 };
export const LEVEL_META = {
  normal:   { label: "Clear",    color: "#2DDBA0" },
  low:      { label: "Low",      color: "#F2C94C" },
  moderate: { label: "Moderate", color: "#F5A524" },
  high:     { label: "High",     color: "#F0525D" },
  critical: { label: "Critical", color: "#FF3B4E" },
};
export const LEVEL_TONE = { normal: "mint", low: "yellow", moderate: "amber", high: "red", critical: "red" };

export function levelOf(road) {
  const raw = String(road?.current_priority_level || road?.current_status || "normal").toLowerCase();
  if (raw === "severe") return "high";
  return LEVEL_META[raw] ? raw : "normal";
}
export const parkedPctOf = (road) => Number(road?.current_parked_space_pct || 0);
export const humanCause = (c) => (c ? String(c).replace(/_/g, " ").replace(/^./, (x) => x.toUpperCase()) : "Not identified");
export function num(v, d = 1) { const n = Number(v); return Number.isFinite(n) ? n.toFixed(d) : "0"; }
export function fmtDur(sec) {
  const s = Number(sec) || 0;
  return s < 120 ? `${Math.round(s)} s` : `${(s / 60).toFixed(1)} min`;
}
// Road width in metres, derived from parked width / parked share (null when nothing is parked).
export function roadWidth(road) {
  const p = parkedPctOf(road), w = Number(road?.current_parked_width_meters || 0);
  return p > 0 && w > 0 ? w / (p / 100) : null;
}
