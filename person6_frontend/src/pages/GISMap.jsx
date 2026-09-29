import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { MapContainer, TileLayer, Marker, Circle, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useData } from "../data";
import { Panel, Chip, Btn, Meter, Empty, OfflineBanner } from "../components/ui";
import { getRoadName } from "../utils/roadNames";
import { levelOf, parkedPctOf, humanCause, num, fmtDur, roadWidth, LEVEL_META, LEVEL_TONE } from "../utils/status";

// Fallback coordinates for the demo roads (same values Person 5's map uses).
const LOC = {
  ROAD_001: [28.5355, 77.391], ROAD_002: [28.6139, 77.209], ROAD_003: [28.6692, 77.4538], ROAD_004: [28.4089, 77.3178],
};
// Free tile sources that need no API key (CARTO's dark tiles now require one).
const OSM = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const BASES = {
  dark: { label: "Dark", url: OSM, attr: "&copy; OpenStreetMap contributors", cls: "dark-tiles" },
  street: { label: "Street", url: OSM, attr: "&copy; OpenStreetMap contributors", cls: "" },
  satellite: { label: "Satellite", url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attr: "Tiles &copy; Esri", cls: "" },
};
const GROUP = { all: () => true, critical: (l) => l === "critical" || l === "high", moderate: (l) => l === "moderate" || l === "low", normal: (l) => l === "normal" };

function Fit({ pts }) {
  const map = useMap();
  useEffect(() => { if (pts.length) map.fitBounds(L.latLngBounds(pts), { padding: [70, 70], maxZoom: 13 }); }, [pts.length]); // eslint-disable-line
  return null;
}

const sign = (color, pct, on) => L.divIcon({
  className: "",
  html: `<div style="transform:translate(-50%,-50%);min-width:44px;padding:3px 7px;background:${color};color:#060D1B;border:${on ? "3px solid #fff" : "2px solid #060D1B"};border-radius:6px;text-align:center;font:800 13px 'JetBrains Mono',monospace;box-shadow:0 2px 10px rgba(0,0,0,.6)">-${Math.round(pct)}%</div>`,
  iconSize: [0, 0],
});

export default function GISMap() {
  const { roads, events, zones, online } = useData();
  const [filter, setFilter] = useState("all");
  const [sel, setSel] = useState(null);
  const [base, setBase] = useState("dark");

  const list = useMemo(() => roads.map((r) => {
    const loc = LOC[r.id] || [Number(r.latitude), Number(r.longitude)];
    return { ...r, pos: loc, level: levelOf(r), zone: zones.find((z) => z.road_id === r.id) };
  }).sort((a, b) => parkedPctOf(b) - parkedPctOf(a)), [roads, zones]);

  const shown = list.filter((r) => GROUP[filter](r.level));
  const placed = shown.filter((r) => Number.isFinite(r.pos[0]) && r.pos[0] !== 0);
  const cnt = (k) => list.filter((r) => GROUP[k](r.level)).length;
  const road = list.find((r) => r.id === sel);
  const totalLoss = list.reduce((s, r) => s + Number(r.current_parked_width_meters || 0), 0);
  const dwell = events.length ? events.reduce((s, e) => s + Number(e.duration_sec || 0), 0) / events.length : 0;
  const w = road ? roadWidth(road) : null;

  return (
    <div className="space-y-5">
      <OfflineBanner show={online === false} />
      <div className="flex flex-wrap items-center gap-2">
        <span className="eyebrow mr-2">GIS corridor topology</span>
        {[["all", "All corridors", "muted"], ["critical", "Critical", "red"], ["moderate", "Moderate", "amber"], ["normal", "Normal", "mint"]].map(([k, label, tone]) => (
          <button key={k} onClick={() => setFilter(k)} aria-pressed={filter === k}>
            <Chip tone={filter === k ? tone : "muted"} className={filter === k ? "ring-1 ring-white/30" : "opacity-70"}>{label} {cnt(k)}</Chip>
          </button>
        ))}
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_380px]">
        <div className="panel relative h-[560px] overflow-hidden">
          {placed.length === 0 ? (
            <div className="flex h-full items-center justify-center p-6"><Empty title="Nothing to plot">No corridors with coordinates match this filter. Seed roads with person5_gis/seed_roads.py.</Empty></div>
          ) : (
            <MapContainer center={[28.6, 77.3]} zoom={10} scrollWheelZoom style={{ height: "100%", width: "100%" }}>
              <TileLayer key={base} attribution={BASES[base].attr} url={BASES[base].url} className={BASES[base].cls} maxZoom={19} />
              <Fit pts={placed.map((r) => r.pos)} />
              {placed.map((r) => {
                const c = LEVEL_META[r.level].color;
                return (
                  <React.Fragment key={r.id}>
                    <Circle center={r.pos} radius={1100} pathOptions={{ color: c, fillColor: c, fillOpacity: 0.16, weight: 2, dashArray: r.is_chronic || r.zone ? "8 6" : undefined }} />
                    <Marker position={r.pos} icon={sign(c, parkedPctOf(r), r.id === sel)} eventHandlers={{ click: () => setSel(r.id) }} />
                  </React.Fragment>
                );
              })}
            </MapContainer>
          )}

          <div role="group" aria-label="Map style" className="panel absolute right-4 top-4 z-[1000] flex overflow-hidden p-1">
            {Object.entries(BASES).map(([k, b]) => (
              <button key={k} onClick={() => setBase(k)} aria-pressed={base === k}
                className={`rounded px-3 py-1.5 text-xs font-bold transition-colors ${base === k ? "bg-mint text-ink-950" : "text-ink-100 hover:bg-ink-600"}`}>{b.label}</button>
            ))}
          </div>

          {road && (
            <div className="panel absolute bottom-4 left-4 z-[1000] w-[320px] max-w-[calc(100%-2rem)] p-4 shadow-2xl">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <Chip tone={LEVEL_TONE[road.level]}>{LEVEL_META[road.level].label}</Chip>
                  <h3 className="mt-2 text-lg font-extrabold text-white">{getRoadName(road.id, road.name)}</h3>
                </div>
                <button onClick={() => setSel(null)} aria-label="Close" className="text-ink-300 hover:text-white">✕</button>
              </div>
              <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
                {[
                  ["Road width", w ? `${num(w, 1)} m` : "n/a"],
                  ["Avg occupied", `${num(road.current_parked_width_meters, 2)} m`],
                  ["Repeat sightings", road.zone?.occurrence_count ?? 0],
                  ["Severity score", road.zone ? `${num(road.zone.severity_score, 0)}/100` : "n/a"],
                ].map(([k, v]) => (
                  <div key={k} className="rounded bg-ink-900 px-2.5 py-2"><dt className="eyebrow">{k}</dt><dd className="mono mt-1 text-sm font-bold text-white">{v}</dd></div>
                ))}
              </dl>
              <p className="mt-3 text-xs text-ink-300">Primary cause</p>
              <p className="text-sm font-bold text-mint">{humanCause(road.current_dominant_cause)}</p>
              {road.zone?.notes && <p className="mt-1 text-xs text-ink-300">{road.zone.notes}</p>}
              <Link to={`/intervention?road=${road.id}`}><Btn variant="mint" className="mt-3 w-full">See recommended action</Btn></Link>
            </div>
          )}
        </div>

        <Panel eyebrow="Ranked by capacity reduction and recurrence" title="Chokepoint leaderboard" bodyClass="p-3">
          <div className="mb-3 grid grid-cols-2 gap-2">
            <div className="rounded-md bg-ink-900 px-3 py-2"><div className="eyebrow">Total width lost</div><div className="mono mt-1 text-xl font-bold text-mint">{num(totalLoss, 2)} m</div></div>
            <div className="rounded-md bg-ink-900 px-3 py-2"><div className="eyebrow">Avg dwell</div><div className="mono mt-1 text-xl font-bold text-mint">{fmtDur(dwell)}</div></div>
          </div>
          {list.length === 0 && <Empty title="No corridors">Seed roads to populate the leaderboard.</Empty>}
          <ol className="space-y-2">
            {list.map((r, i) => {
              const c = LEVEL_META[r.level].color;
              const rw = roadWidth(r);
              return (
                <li key={r.id}>
                  <button onClick={() => setSel(r.id)} className={`w-full rounded-lg border p-3 text-left transition-colors ${r.id === sel ? "border-mint bg-ink-600" : "border-ink-600 bg-ink-800 hover:bg-ink-700"}`}>
                    <div className="flex items-center gap-3">
                      <span className="mono flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold text-ink-950" style={{ background: c }}>{i + 1}</span>
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm font-bold text-white">{getRoadName(r.id, r.name)}</div>
                        <div className="text-xs text-ink-300">{r.zone ? `Severity ${num(r.zone.severity_score, 0)} · ${r.zone.occurrence_count} sightings` : "No recurrence flagged"}</div>
                      </div>
                      <span className="mono text-sm font-bold" style={{ color: c }}>-{num(parkedPctOf(r))}%</span>
                    </div>
                    <div className="mt-2"><Meter value={parkedPctOf(r)} color={c} /></div>
                    <div className="mt-1.5 flex justify-between text-[11px] text-ink-300">
                      <span>Occupied {num(r.current_parked_width_meters, 2)} m{rw ? ` of ${num(rw, 1)} m` : ""}</span>
                      <span>{humanCause(r.current_dominant_cause)}</span>
                    </div>
                  </button>
                </li>
              );
            })}
          </ol>
        </Panel>
      </div>
    </div>
  );
}
