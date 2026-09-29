import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { AlertTriangle, CheckCircle2, ArrowUpRight, Search } from "lucide-react";
import { useData } from "../data";
import { api } from "../api";
import LaneStrip from "../components/LaneStrip";
import VideoDetectionPlayer from "../components/VideoDetectionPlayer";
import { Panel, Chip, Btn, Kpi, Empty, OfflineBanner, TONES, tipStyle } from "../components/ui";
import { getRoadName } from "../utils/roadNames";
import { levelOf, parkedPctOf, humanCause, num, fmtDur, roadWidth, LEVEL_META, LEVEL_TONE, RANK } from "../utils/status";

export default function LiveMonitoring() {
  const { roads, events, alerts, online, reload } = useData();
  const [sel, setSel] = useState(null);
  const [q, setQ] = useState("");
  const [hidden, setHidden] = useState({});

  const sorted = useMemo(
    () => [...roads].sort((a, b) => RANK[levelOf(b)] - RANK[levelOf(a)] || parkedPctOf(b) - parkedPctOf(a)),
    [roads]
  );
  const road = sorted.find((r) => r.id === sel) || sorted[0];
  const worst = sorted[0];
  const alert = alerts.find((a) => a.status !== "acknowledged");
  const alertRoad = alert && roads.find((r) => r.id === alert.road_id);
  const meanDwell = events.length ? events.reduce((s, e) => s + Number(e.duration_sec || 0), 0) / events.length : 0;
  const active = events.filter((e) => e.status === "active").length;
  const types = [...new Set(events.map((e) => e.vehicle_type))];
  const rows = events
    .filter((e) => !hidden[e.vehicle_type])
    .filter((e) => !q || `${e.event_id} ${e.vehicle_type} ${e.cause} ${getRoadName(e.road_id)}`.toLowerCase().includes(q.toLowerCase()))
    .slice(0, 10);
  const roadEvents = road ? events.filter((e) => e.road_id === road.id).slice(0, 6) : [];
  const chart = sorted.map((r) => ({ name: getRoadName(r.id, r.name), pct: Number(parkedPctOf(r).toFixed(1)), color: LEVEL_META[levelOf(r)].color }));
  const width = road ? roadWidth(road) : null;

  async function ack() {
    try { await api.acknowledgeAlert(alert.id); reload(); } catch (e) { console.error(e); }
  }

  return (
    <div className="space-y-5">
      <OfflineBanner show={online === false} />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Usable space deficit" tone={worst && parkedPctOf(worst) >= 5 ? "red" : "mint"}
          value={worst ? `-${num(parkedPctOf(worst))}%` : "0%"}
          sub={worst ? `${getRoadName(worst.id, worst.name)} · ${num(worst.current_parked_width_meters, 2)} m taken` : "No roads loaded"} />
        <Kpi label="Active obstructions" tone="cyan" value={active || events.length} sub={`${events.length} events logged · ${types.length} vehicle types`} />
        <Kpi label="Monitored corridors" tone="mint" value={roads.length} sub={`${sorted.filter((r) => levelOf(r) !== "normal").length} need attention`} />
        <Kpi label="Mean obstruction dwell" tone="amber" value={fmtDur(meanDwell)} sub="Average time a vehicle stays stopped" />
      </div>

      {alert ? (
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-[#F0525D66] bg-[#F0525D14] px-5 py-4">
          <div className="flex items-start gap-4">
            <AlertTriangle className="mt-1 shrink-0 text-[#F0525D]" size={26} />
            <div>
              <div className="text-xl font-extrabold text-white">
                Road-space loss{alertRoad ? `: -${num(parkedPctOf(alertRoad))}%` : ""} <span className="text-base font-semibold text-ink-200">· {getRoadName(alert.road_id)}</span>
              </div>
              <p className="mt-1 max-w-3xl text-sm text-ink-200">{alert.message}</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Btn variant="ghost" onClick={ack}>Acknowledge</Btn>
            <Link to={`/intervention?road=${alert.road_id}`}><Btn variant="mint">Open intervention</Btn></Link>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-3 rounded-lg border border-[#2DDBA055] bg-[#2DDBA010] px-5 py-4 text-sm text-ink-100">
          <CheckCircle2 className="text-mint" size={22} /> No open alerts. New obstruction alerts appear here as the pipeline reports them.
        </div>
      )}

      {road ? (
        <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
          <Panel eyebrow="Corridor view" title={getRoadName(road.id, road.name)}
            aside={<div className="flex gap-2"><Chip tone={LEVEL_TONE[levelOf(road)]}>{LEVEL_META[levelOf(road)].label}</Chip>{road.is_chronic && <Chip tone="amber">Chronic</Chip>}</div>}>
            <div className="mt-2"><VideoDetectionPlayer roadId={road.id} /></div>
            <h3 className="eyebrow mb-2 mt-5">Road-space view</h3>
            <LaneStrip parkedPct={parkedPctOf(road)} level={levelOf(road)} height={64} />
            <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                ["Lost to parking", `${num(parkedPctOf(road))}%`],
                ["Width taken", `${num(road.current_parked_width_meters, 2)} m`],
                ["Road width", width ? `${num(width, 1)} m` : "n/a"],
                ["Lanes busy", `${num(road.current_occupancy_pct, 0)}%`],
              ].map(([k, v]) => (
                <div key={k} className="rounded-md bg-ink-900 px-3 py-2.5">
                  <dt className="eyebrow">{k}</dt>
                  <dd className="mono mt-1 text-lg font-bold text-white">{v}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-3 text-sm text-ink-300">Main cause: <b className="text-ink-100">{humanCause(road.current_dominant_cause)}</b>. The strip above shows the same road as a cross-section, built from the analysis data.</p>

            <h3 className="eyebrow mb-2 mt-5">Vehicles stopped on this corridor</h3>
            {roadEvents.length === 0 ? (
              <p className="text-sm text-ink-300">No obstruction events recorded for this road yet.</p>
            ) : (
              <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {roadEvents.map((e) => (
                  <li key={e.event_id} className="rounded-md border border-ink-600 bg-ink-900 px-3 py-2 text-xs">
                    <div className="flex justify-between"><b className="text-white">#{e.vehicle_id} {e.vehicle_type}</b><span className="mono text-mint">{fmtDur(e.duration_sec)}</span></div>
                    <div className="mt-1 text-ink-300">{num(e.road_space_loss_pct)}% width · {humanCause(e.cause)}</div>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <div className="space-y-5">
            <Panel eyebrow="Switch corridor" title="Monitored roads" bodyClass="p-2">
              <ul>
                {sorted.map((r) => {
                  const on = r.id === road.id;
                  return (
                    <li key={r.id}>
                      <button onClick={() => setSel(r.id)} aria-pressed={on}
                        className={`flex w-full items-center justify-between gap-3 rounded-md px-3 py-2.5 text-left transition-colors ${on ? "bg-ink-600" : "hover:bg-ink-700"}`}>
                        <span>
                          <span className="block text-sm font-bold text-white">{getRoadName(r.id, r.name)}</span>
                          <span className="text-xs text-ink-300">{humanCause(r.current_dominant_cause)}</span>
                        </span>
                        <span className="mono text-sm font-bold" style={{ color: LEVEL_META[levelOf(r)].color }}>-{num(parkedPctOf(r))}%</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </Panel>

            <Panel eyebrow="Target classification filter" title="Vehicle types">
              {types.length === 0 ? <p className="text-sm text-ink-300">Appears once events are logged.</p> : (
                <div className="grid grid-cols-2 gap-2">
                  {types.map((t) => (
                    <label key={t} className="flex cursor-pointer items-center gap-2 rounded-md border border-ink-600 bg-ink-900 px-3 py-2 text-sm">
                      <input type="checkbox" checked={!hidden[t]} onChange={() => setHidden((h) => ({ ...h, [t]: !h[t] }))} />
                      <span className="capitalize">{t}</span>
                      <span className="mono ml-auto text-xs text-ink-300">{events.filter((e) => e.vehicle_type === t).length}</span>
                    </label>
                  ))}
                </div>
              )}
            </Panel>

            <Panel eyebrow="Loss by corridor" title="Share of width lost">
              <div style={{ height: 150 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chart} margin={{ top: 8, right: 4, left: -18 }}>
                    <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#8C9BB8" }} axisLine={false} tickLine={false} interval={0} />
                    <YAxis unit="%" tick={{ fontSize: 10, fill: "#8C9BB8" }} axisLine={false} tickLine={false} />
                    <Tooltip cursor={{ fill: "#1C3156" }} contentStyle={tipStyle} formatter={(v) => [`${v}%`, "Lost"]} />
                    <Bar dataKey="pct" radius={[3, 3, 0, 0]}>{chart.map((c, i) => <Cell key={i} fill={c.color} />)}</Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>
          </div>
        </div>
      ) : (
        <Empty title="No roads yet">Seed the demo roads (person5_gis/seed_roads.py) or run the detection pipeline. Roads appear here as soon as the backend has data.</Empty>
      )}

      <Panel eyebrow="Stream synchronized" title="Live event detection log"
        aside={
          <label className="flex items-center gap-2 rounded-md border border-ink-500 bg-ink-900 px-3 py-2 text-sm">
            <Search size={15} className="text-ink-300" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter events" aria-label="Filter events"
              className="w-40 bg-transparent text-ink-100 outline-none placeholder:text-ink-400" />
          </label>
        } bodyClass="p-0 pt-3">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead>
              <tr className="eyebrow border-b border-ink-600 text-left">
                {["Event / class", "Corridor", "Dwell", "Width loss", "Attributed cause", "Status", ""].map((h) => <th key={h} className="px-4 py-3 font-medium">{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((e) => (
                <tr key={e.event_id} className="border-b border-ink-700 last:border-b-0 hover:bg-ink-700/50">
                  <td className="px-4 py-3"><div className="mono text-xs text-ink-300">{e.event_id}</div><div className="font-bold capitalize text-white">#{e.vehicle_id} {e.vehicle_type}</div></td>
                  <td className="px-4 py-3">{getRoadName(e.road_id)}</td>
                  <td className="mono px-4 py-3">{fmtDur(e.duration_sec)}</td>
                  <td className="mono px-4 py-3 font-bold" style={{ color: TONES.red }}>-{num(e.road_space_loss_pct)}%</td>
                  <td className="px-4 py-3">{humanCause(e.cause)} <span className="mono text-xs text-ink-300">{Math.round((e.cause_confidence || 0) * 100)}%</span></td>
                  <td className="px-4 py-3"><Chip tone={e.status === "active" ? "red" : "mint"}>{e.status || "logged"}</Chip></td>
                  <td className="px-4 py-3 text-right"><Link to={`/analysis?road=${e.road_id}`} className="inline-flex items-center gap-1 font-bold text-mint hover:underline">Investigate <ArrowUpRight size={14} /></Link></td>
                </tr>
              ))}
              {rows.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-ink-300">No events match. Run the pipeline (python run_closed_loop.py) to log obstruction events.</td></tr>}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
