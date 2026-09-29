import { useEffect, useMemo, useState, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { RefreshCw, FlaskConical, CheckCircle2, XCircle } from "lucide-react";
import { useData } from "../data";
import { api } from "../api";
import LaneStrip from "../components/LaneStrip";
import { Panel, Chip, Btn, Meter, Empty, OfflineBanner, TONES } from "../components/ui";
import { getRoadName } from "../utils/roadNames";
import { levelOf, parkedPctOf, humanCause, num, fmtDur, RANK } from "../utils/status";

export default function Intervention() {
  const { roads, zones, online } = useData();
  const [params, setParams] = useSearchParams();
  const [recs, setRecs] = useState([]);
  const [outcomes, setOutcomes] = useState([]);
  const [pick, setPick] = useState(0);
  const [sims, setSims] = useState({});
  const [decision, setDecision] = useState({});
  const [busy, setBusy] = useState(null);
  const [err, setErr] = useState(null);

  const sorted = useMemo(() => [...roads].sort((a, b) => RANK[levelOf(b)] - RANK[levelOf(a)] || parkedPctOf(b) - parkedPctOf(a)), [roads]);
  const road = sorted.find((r) => r.id === params.get("road")) || sorted[0];
  const zone = road && zones.find((z) => z.road_id === road.id);

  const load = useCallback(async () => {
    if (!road) return;
    try {
      const data = await api.listRecommendations(road.id);
      const seen = new Set();
      const uniq = data.filter((r) => (seen.has(r.intervention) ? false : seen.add(r.intervention)));
      uniq.sort((a, b) => Number(a.priority_rank ?? 999) - Number(b.priority_rank ?? 999));
      setRecs(uniq);
      setPick(0);
      setErr(null);
    } catch (e) { setErr("Could not load recommendations."); }
  }, [road?.id]); // eslint-disable-line

  useEffect(() => { load(); }, [load]);
  useEffect(() => { api.listOutcomes().then(setOutcomes).catch(() => setOutcomes([])); }, []);

  const top = recs[pick];
  const sim = top && sims[top.intervention];
  const dec = top && decision[`${road?.id}|${top.intervention}`];
  const roadOutcomes = outcomes.filter((o) => o.road_id === road?.id);

  async function generate() {
    setBusy("gen");
    try { await api.generateRecommendations(road.id); await load(); } catch (e) { setErr("Could not generate recommendations."); }
    setBusy(null);
  }
  async function simulate(r) {
    setBusy(r.intervention);
    try { const s = await api.simulate(r.road_id, r.intervention); setSims((p) => ({ ...p, [r.intervention]: s })); } catch (e) { setErr("Simulation failed."); }
    setBusy(null);
  }
  async function decide(accepted) {
    try {
      await api.sendFeedback({ road_id: road.id, feedback_type: "recommendation", original_value: top.intervention, accepted });
      setDecision((p) => ({ ...p, [`${road.id}|${top.intervention}`]: accepted ? "approved" : "rejected" }));
    } catch (e) { setErr("Could not save the decision."); }
  }

  if (!road) return (<div><OfflineBanner show={online === false} /><Empty title="No roads yet">Seed roads and run the pipeline to get recommendations.</Empty></div>);

  return (
    <div className="space-y-5">
      <OfflineBanner show={online === false} />
      {err && <div role="alert" className="rounded-lg border border-[#F0525D66] bg-[#F0525D12] px-4 py-3 text-sm">{err}</div>}

      <div className="panel flex flex-wrap items-center justify-between gap-3 px-5 py-4">
        <p className="max-w-3xl text-sm text-ink-200">
          LaneLogic does not remove vehicles. It finds the problem, explains it, recommends an action and measures the result. The authority decides and acts.
        </p>
        <Chip tone="mint">Closed loop: detect, explain, recommend, measure</Chip>
      </div>

      <div role="tablist" aria-label="Choose a corridor" className="flex flex-wrap gap-2">
        {sorted.map((r) => (
          <button key={r.id} role="tab" aria-selected={r.id === road.id} onClick={() => setParams({ road: r.id })}
            className={`rounded-md px-4 py-2 text-sm font-bold transition-colors ${r.id === road.id ? "bg-mint text-ink-950" : "border border-ink-500 text-ink-100 hover:bg-ink-600"}`}>
            {getRoadName(r.id, r.name)}
          </button>
        ))}
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_400px]">
        <Panel eyebrow="Policy intervention" title={top ? top.intervention : "Recommended action"}
          aside={<Btn variant="ghost" onClick={generate} disabled={busy === "gen"}><RefreshCw size={14} className={busy === "gen" ? "animate-spin" : ""} /> {recs.length ? "Refresh" : "Generate"}</Btn>}>
          {!top ? (
            <Empty title="No recommendation for this corridor yet">Press Generate to create ranked actions from this road's current cause, or run the closed-loop pipeline.</Empty>
          ) : (
            <>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <Chip tone="red">{humanCause(top.cause)}</Chip>
                {zone && <Chip tone="amber">{zone.occurrence_count} repeat sightings</Chip>}
                <Chip tone="muted">Rank #{top.priority_rank}</Chip>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <div className="rounded-md bg-ink-900 p-3"><div className="eyebrow">Match score</div><div className="mono mt-1 text-3xl font-bold text-mint">{Math.round(top.expected_benefit_score)}<span className="text-base text-ink-300">/100</span></div></div>
                <div className="rounded-md bg-ink-900 p-3"><div className="eyebrow">Space recovery</div><div className="mt-2"><Meter value={top.expected_benefit_score} color={TONES.mint} height={8} /></div></div>
                <div className="rounded-md bg-ink-900 p-3"><div className="eyebrow">Implementation effort</div><div className="mt-2"><Meter value={top.implementation_difficulty_score} color={TONES.amber} height={8} /></div><div className="mono mt-1 text-xs text-ink-300">{Math.round(top.implementation_difficulty_score)}/100</div></div>
              </div>

              <p className="mt-4 max-w-2xl text-sm leading-relaxed text-ink-200">{top.rationale}</p>

              <div className="mt-4 flex flex-wrap gap-2">
                <Btn variant="ghost" onClick={() => simulate(top)} disabled={busy === top.intervention}><FlaskConical size={15} /> {sim ? "Run simulation again" : "Simulate the effect"}</Btn>
              </div>

              {sim && (
                <div className="mt-4 rounded-lg border border-ink-600 bg-ink-900 p-4">
                  <div className="eyebrow mb-2">Simulated clearance</div>
                  <LaneStrip parkedPct={sim.simulated_loss_pct} ghostPct={sim.baseline_loss_pct} level="normal" height={34} animate={false} />
                  <dl className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
                    {[
                      ["Loss now", `${num(sim.baseline_loss_pct)}%`], ["Loss after", `${num(sim.simulated_loss_pct)}%`],
                      ["Recovery", `+${num(sim.simulated_recovery_pct)}%`], ["Dwell", `${fmtDur(sim.baseline_avg_duration_sec)} to ${fmtDur(sim.simulated_avg_duration_sec)}`],
                      ["Feasibility", `${num(sim.feasibility_score, 1)}`], ["Disruption", `${num(sim.disruption_score, 1)}`], ["Confidence", `${Math.round(sim.confidence_score * 100)}%`],
                      ["Data", sim.data_source === "demo_default" ? "Default figures" : "This road's history"],
                    ].map(([k, v]) => <div key={k} className="rounded bg-ink-800 px-2.5 py-2"><dt className="eyebrow">{k}</dt><dd className="mono mt-1 font-bold text-white">{v}</dd></div>)}
                  </dl>
                  <p className="mt-2 text-[11px] text-ink-300">Dashed outline is today's parked width. {sim.disclaimer}</p>
                </div>
              )}

              <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[#38C6F455] bg-[#38C6F410] px-4 py-3">
                <div>
                  <div className="text-sm font-bold text-white">Municipal authority authorization required</div>
                  <div className="text-xs text-ink-300">Your decision is saved to the backend and used to improve future ranking.</div>
                </div>
                {dec ? (
                  <Chip tone={dec === "approved" ? "mint" : "red"}>{dec === "approved" ? <CheckCircle2 size={13} /> : <XCircle size={13} />} Decision saved: {dec}</Chip>
                ) : (
                  <div className="flex gap-2">
                    <Btn variant="danger" onClick={() => decide(false)}>Reject</Btn>
                    <Btn variant="mint" onClick={() => decide(true)}>Approve and log order</Btn>
                  </div>
                )}
              </div>
            </>
          )}
        </Panel>

        <Panel eyebrow="Measured efficacy" title="Closed-loop validation">
          {roadOutcomes.length === 0 ? (
            <Empty title="No result recorded yet">After an action is carried out, record before/after numbers with POST /interventions/outcome. They show up here as measured change, not as a prediction.</Empty>
          ) : (
            roadOutcomes.map((o) => (
              <div key={o.id} className="mb-4 last:mb-0">
                <div className="flex items-center justify-between"><b className="text-sm text-white">{o.intervention_type}</b><Chip tone="mint">{o.implementation_date}</Chip></div>
                <ul className="mt-3 space-y-3">
                  {Object.keys(o.baseline_metrics || {}).map((k) => {
                    const b = Number(o.baseline_metrics[k]), p = Number(o.post_metrics?.[k] ?? 0), max = Math.max(b, p, 1);
                    return (
                      <li key={k}>
                        <div className="mb-1 flex justify-between text-xs"><span className="text-ink-200">{humanCause(k)}</span><span className="mono text-ink-100">{num(b)} to {num(p)}</span></div>
                        <Meter value={b} max={max} color={TONES.red} height={5} /><div className="h-1" /><Meter value={p} max={max} color={TONES.mint} height={5} />
                      </li>
                    );
                  })}
                </ul>
                <p className="mt-3 text-[11px] text-ink-300">{o.is_causal_claim ? "Marked as causal." : "Observed change only. This is not proof the action caused it."}</p>
              </div>
            ))
          )}
        </Panel>
      </div>

      <Panel eyebrow="Decision matrix" title="Candidate interventions, ranked" bodyClass="p-0 pt-3">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead><tr className="eyebrow border-b border-ink-600 text-left">{["Rank / strategy", "Match score", "Effort", "Simulated recovery", "Action"].map((h) => <th key={h} className="px-4 py-3 font-medium">{h}</th>)}</tr></thead>
            <tbody>
              {recs.map((r, i) => {
                const s = sims[r.intervention];
                return (
                  <tr key={r.intervention} className={`border-b border-ink-700 last:border-b-0 ${i === pick ? "bg-ink-600/50" : "hover:bg-ink-700/50"}`}>
                    <td className="px-4 py-3"><span className="mono mr-3 text-ink-300">#{r.priority_rank}</span><b className="text-white">{r.intervention}</b><div className="ml-9 text-xs text-ink-300">{humanCause(r.cause)}</div></td>
                    <td className="mono px-4 py-3 font-bold text-mint">{Math.round(r.expected_benefit_score)}/100</td>
                    <td className="mono px-4 py-3 text-[#F5A524]">{Math.round(r.implementation_difficulty_score)}/100</td>
                    <td className="mono px-4 py-3">{s ? `+${num(s.simulated_recovery_pct)}%` : "-"}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <Btn variant={i === pick ? "mint" : "ghost"} onClick={() => setPick(i)}>{i === pick ? "Selected" : "Select"}</Btn>
                        <Btn variant="ghost" onClick={() => simulate(r)} disabled={busy === r.intervention}>Simulate</Btn>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {recs.length === 0 && <tr><td colSpan={5} className="px-4 py-8 text-center text-ink-300">No candidates yet. Press Generate above.</td></tr>}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
