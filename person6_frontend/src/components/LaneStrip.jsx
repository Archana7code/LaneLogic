import { LEVEL_META } from "../utils/status";

/* Cross-section of a road. The hatched block is the share of width lost to parked vehicles. */
export default function LaneStrip({ parkedPct = 0, level = "normal", height = 40, animate = true, ghostPct = null }) {
  const pct = Math.min(Math.max(Number(parkedPct) || 0, 0), 100);
  const color = LEVEL_META[level]?.color || LEVEL_META.normal.color;
  const ghost = ghostPct == null ? null : Math.min(Math.max(Number(ghostPct) || 0, 0), 100);
  return (
    <div role="img" aria-label={`${pct.toFixed(0)} percent of road width lost, ${(100 - pct).toFixed(0)} percent usable`}
      className="relative w-full overflow-hidden rounded bg-ink-900 ring-1 ring-ink-600" style={{ height }}>
      <div className="absolute inset-y-0 left-1/3 w-[2px] lane-marks" />
      <div className="absolute inset-y-0 left-2/3 w-[2px] lane-marks" />
      <div className="absolute inset-y-0 right-0 w-[3px] bg-mint" />
      {ghost != null && (
        <div className="absolute inset-y-[3px] right-[3px] rounded-[2px] border border-dashed border-white/50" style={{ width: `calc(${ghost}% - 3px)` }} />
      )}
      {pct > 0 && (
        <div className={`absolute inset-y-[3px] right-[3px] rounded-[2px] hatch ${animate ? "park-in" : ""}`}
          style={{ width: `calc(${pct}% - 3px)`, backgroundColor: color, minWidth: 6 }} />
      )}
    </div>
  );
}
