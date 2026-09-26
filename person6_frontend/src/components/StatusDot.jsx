const STATUS_COLOR = {
  normal: "bg-signal-green",
  moderate: "bg-signal-yellow",
  severe: "bg-signal-red",
  chronic: "bg-signal-orange",
};

const STATUS_TEXT = {
  normal: "text-signal-green",
  moderate: "text-yellow-600",
  severe: "text-signal-red",
  chronic: "text-signal-orange",
};

// A small pulsing dot + label, standing in for the pill badges you'd see
// on a generic dashboard. Reads more like a live signal light.
export default function StatusDot({ status, live = false }) {
  const dot = STATUS_COLOR[status] || "bg-slate-400";
  const text = STATUS_TEXT[status] || "text-slate-500";

  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`relative flex h-2 w-2 ${live ? "pulse-dot" : ""}`}>
        <span className={`h-2 w-2 rounded-full ${dot}`} />
      </span>
      <span className={`text-xs font-mono font-medium uppercase tracking-wide ${text}`}>
        {status}
      </span>
    </span>
  );
}
