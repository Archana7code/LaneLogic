import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AreaChart, Area, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { useData } from "../data";
import { api } from "../api";
import { Panel, Chip, Btn, Kpi, Meter, Empty, OfflineBanner, TONES, tipStyle } from "../components/ui";
import { getRoadName } from "../utils/roadNames";
import { levelOf, parkedPctOf, humanCause, num, LEVEL_META, LEVEL_TONE, RANK } from "../utils/status";

const PIE = ["#2DDBA0", "#38C6F4", "#F5A524", "#F0525D", "#A78BFA", "#8C9BB8"];

export default function ProblemAnalysis() {
  const { roads, events, zones, online } = useData();
  const [params, setParams] = useSearchParams();
  const [history, setHistory] = useState([]);
  const [pred, setPred] = useState(null);
  const [models, setModels] = useState(null);

  const sorted = useMemo(() => [...roads].sort((a, b) => RANK[levelOf(b)] - RANK[levelOf(a)] || parkedPctOf(b) - parkedPctOf(a)), [roads]);
  const road = sorted.find((r) => r.id === params.get("road")) || sorted[0];
  const zone = road && zones.find((z) => z.road_id === road.id);
  const roadEvents = road ? events.filter((e) => e.road_id === road.id) : [];
  const topEvent = [...roadEvents].sort((a, b) => Number(b.road_space_loss_pct) - Number(a.road_space_loss_pct))[0];

  useEffect(() => { api.modelVersions().then(setModels).catch(() => setModels(null)); }, []);
  useEffect(() => {
    if (!road) return;
    setHistory([]);
    api.roadHistory(road.id).then(setHistory).catch(() => setHistory([]));
  }, [road?.id]); // eslint-disable-line

  // Explainability: ask the backend's cause model about this road's worst event and show its feature contributions.
  useEffect(() => {
    if (!road) return;
    setPred(null);
    api.predictCause({
      road_id: road.id,
      vehicle_type: topEvent?.vehicle_type || "car",
      duration_sec: Number(topEvent?.duration_sec || 600),
      road_space_loss_pct: Number(topEvent?.road_space_loss_pct ?? parkedPctOf(road)),
      recurrence_score: Number(topEvent?.recurrence_score || zone?.severity_score || 0),
    }).then(setPred).catch(() => setPred(null));
  }, [road?.id, topEvent?.event_id]); // eslint-disable-line

  const data = history.map((h) => ({ w: h.window_index, parked: Number(h.parked_space_pct || h.blocked_pct || 0), busy: Number(h.occupancy_pct || 0) }));
  const peak = data.reduce((m, d) => Math.max(m, d.parked), 0);
  const avg = data.length ? data.reduce((s, d) => s + d.parked, 0) / data.length : 0;
  const causes = useMemo(() => {
    const c = {};
    history.forEach((h) => (c[h.cause] = (c[h.cause] || 0) + 1));
    const t = history.length || 1;
    return Object.entries(c).sort((a, b) => b[1] - a[1]).map(([k, n], i) => ({ name: humanCause(k), n, share: (n / t) * 100, color: PIE[i % PIE.length] }));
  }, [history]);
  const contrib = pred?.feature_contributions ? Object.entries(pred.feature_contributions).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])).slice(0, 6) : [];
  const maxC = contrib.reduce((m, [, v]) => Math.max(m, Math.abs(v)), 0) || 1;
  const modelCount = models ? (Array.isArray(models.versions) ? models.versions.length : Object.keys(models.versions || {}).length) : null;

  if (!road) return (<div><OfflineBanner show={online === false} /><Empty title="No roads yet">Seed roads and run the analysis step to see cause analysis here.</Empty></div>);

  return (
    <div className="space-y-5">
      <OfflineBanner show={online === false} />

      <Panel eyebrow="Explainability engine" title="ML answers: why is the road space being lost?">
        <p className="max-w-3xl text-sm text-ink-200">
          Every obstruction is classified into a cause and broken down into the factors that pushed the decision (vehicle type, dwell time, share of road lost, recurrence). Nothing here is a black box.
        </p>
      </Panel>

      <div role="tablist" aria-label="Choose a corridor" className="flex flex-wrap gap-2">
        {sorted.map((r) => (
          <button key={r.id} role="tab" aria-selected={r.id === road.id} onClick={() => setParams({ road: r.id })}
            className={`rounded-md px-4 py-2 text-sm font-bold transition-colors ${r.id === road.id ? "bg-mint text-ink-950" : "border border-ink-500 text-ink-100 hover:bg-ink-600"}`}>
            {getRoadName(r.id, r.name)}
          </button>
        ))}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Lost right now" tone={LEVEL_TONE[levelOf(road)]} value={`-${num(parkedPctOf(road))}%`} sub={LEVEL_META[levelOf(road)].label + " priority"} />
        <Kpi label="Worst window" tone="red" value={`-${num(peak)}%`} sub={`Across ${data.length} analysis windows`} />
        <Kpi label="Average loss" tone="amber" value={`-${num(avg)}%`} sub="Mean over all windows" />
        <Kpi label="Recurrence" tone="cyan" value={zone ? zone.occurrence_count : 0} sub={zone ? `Chronic zone · severity ${num(zone.severity_score, 0)}/100` : "Not flagged as chronic"} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_380px]">
        <Panel eyebrow="Daily obstruction breakdown" title="Parked share over analysis windows">
          {data.length === 0 ? <Empty title="No windows yet">Run the analysis step for this road and its history plots here.</Empty> : (
            <div className="mt-2" style={{ height: 290 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data} margin={{ left: -12, right: 8, top: 8 }}>
                  <CartesianGrid stroke="#1C3156" vertical={false} />
                  <XAxis dataKey="w" tick={{ fontSize: 11, fill: "#8C9BB8" }} axisLine={{ stroke: "#1C3156" }} tickLine={false} />
                  <YAxis unit="%" domain={[0, 100]} tick={{ fontSize: 11, fill: "#8C9BB8" }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={tipStyle} labelFormatter={(l) => `Window ${l}`} formatter={(v, n) => [`${Number(v).toFixed(1)}%`, n === "parked" ? "Lost to parking" : "Lanes busy"]} />
                  <Area type="stepAfter" dataKey="parked" stroke="#F0525D" strokeWidth={2.5} fill="#F0525D" fillOpacity={0.22} />
                  <Line type="monotone" dataKey="busy" stroke="#38C6F4" strokeWidth={2} dot={false} strokeDasharray="6 5" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
          <p className="mt-1 text-xs text-ink-300">Red area: road width lost to parked vehicles. Cyan dashed line: how busy the lanes are.</p>
        </Panel>

        <Panel eyebrow="Post-hoc attribution" title="Cause attribution">
          {causes.length === 0 ? <Empty title="No causes yet">Causes appear once analysis windows exist.</Empty> : (
            <>
              <div className="relative mx-auto" style={{ height: 190 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={causes} dataKey="n" nameKey="name" innerRadius={58} outerRadius={82} paddingAngle={2} stroke="none">{causes.map((c, i) => <Cell key={i} fill={c.color} />)}</Pie>
                    <Tooltip contentStyle={tipStyle} formatter={(v, n) => [`${v} windows`, n]} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                  <span className="mono text-2xl font-bold text-white">{Math.round(causes[0].share)}%</span>
                  <span className="text-[11px] text-ink-300">{causes[0].name}</span>
                </div>
              </div>
              <ul className="mt-3 space-y-2">
                {causes.map((c) => (
                  <li key={c.name} className="flex items-center justify-between text-sm">
                    <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: c.color }} />{c.name}</span>
                    <span className="mono text-ink-200">{Math.round(c.share)}%</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Panel>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_380px]">
        <Panel eyebrow="Feature attribution" title={pred ? `Predicted cause: ${humanCause(pred.cause)}` : "Feature attribution"}
          aside={pred && <Chip tone="mint">{Math.round(pred.confidence * 100)}% confidence</Chip>}>
          {!pred ? <Empty title="Waiting for the cause model">Needs the backend endpoint /causes/predict to answer.</Empty> : (
            <>
              <p className="mt-1 text-sm text-ink-200">{pred.explanation}</p>
              <p className="eyebrow mb-3 mt-4">Basis: {topEvent ? `worst logged event (#${topEvent.vehicle_id} ${topEvent.vehicle_type})` : "road summary, no events logged yet"}</p>
              <ul className="space-y-3">
                {contrib.map(([k, v]) => (
                  <li key={k}>
                    <div className="mb-1 flex justify-between text-sm"><span className="font-semibold text-ink-100">{humanCause(k)}</span>
                      <span className="mono font-bold" style={{ color: v >= 0 ? TONES.mint : TONES.red }}>{v >= 0 ? "+" : ""}{Number(v).toFixed(2)}</span></div>
                    <Meter value={Math.abs(v)} max={maxC} color={v >= 0 ? TONES.mint : TONES.red} />
                  </li>
                ))}
              </ul>
              {pred.triggered_rules?.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">{pred.triggered_rules.map((r) => <Chip key={r} tone="cyan">{humanCause(r)}</Chip>)}</div>
              )}
            </>
          )}
        </Panel>

        <Panel eyebrow="Model registry" title="Model in use">
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between border-b border-ink-700 pb-2"><dt className="text-ink-300">Deployed version</dt><dd className="mono font-bold text-mint">{models?.deployed_version ? String(models.deployed_version).slice(0, 24) : "n/a"}</dd></div>
            <div className="flex justify-between border-b border-ink-700 pb-2"><dt className="text-ink-300">Versions registered</dt><dd className="mono font-bold text-white">{modelCount ?? "n/a"}</dd></div>
            <div className="flex justify-between"><dt className="text-ink-300">Events on this road</dt><dd className="mono font-bold text-white">{roadEvents.length}</dd></div>
          </dl>
          <p className="mt-3 text-xs text-ink-300">Accept or reject recommendations on the Intervention page to feed decisions back to the model.</p>
        </Panel>
      </div>

      <Panel eyebrow="Section 04" title="Historical bottleneck chronology" bodyClass="p-0 pt-3">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[700px] text-sm">
            <thead><tr className="eyebrow border-b border-ink-600 text-left">{["Corridor", "Primary cause", "Sightings", "Severity", "Notes", ""].map((h) => <th key={h} className="px-4 py-3 font-medium">{h}</th>)}</tr></thead>
            <tbody>
              {zones.map((z) => (
                <tr key={z.id} className="border-b border-ink-700 last:border-b-0 hover:bg-ink-700/50">
                  <td className="px-4 py-3 font-bold text-white">{getRoadName(z.road_id)}</td>
                  <td className="px-4 py-3">{humanCause(z.dominant_cause)}</td>
                  <td className="mono px-4 py-3">{z.occurrence_count}</td>
                  <td className="px-4 py-3"><div className="flex items-center gap-2"><span className="mono w-8">{num(z.severity_score, 0)}</span><div className="w-24"><Meter value={z.severity_score} color={TONES.red} /></div></div></td>
                  <td className="max-w-xs px-4 py-3 text-ink-300">{z.notes || "-"}</td>
                  <td className="px-4 py-3 text-right"><Link to={`/intervention?road=${z.road_id}`}><Btn variant="ghost">Recommend action</Btn></Link></td>
                </tr>
              ))}
              {zones.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-ink-300">No chronic zones flagged yet. They appear once the same obstruction recurs across enough windows.</td></tr>}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
