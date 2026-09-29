import { WifiOff } from "lucide-react";

export const TONES = { mint: "#2DDBA0", red: "#F0525D", amber: "#F5A524", cyan: "#38C6F4", yellow: "#F2C94C", muted: "#8C9BB8" };

export function Panel({ title, eyebrow, aside, children, className = "", bodyClass = "p-4" }) {
  return (
    <section className={`panel ${className}`}>
      {(title || eyebrow || aside) && (
        <header className="flex items-start justify-between gap-3 px-4 pt-4">
          <div>
            {eyebrow && <div className="eyebrow mb-1">{eyebrow}</div>}
            {title && <h2 className="text-[17px] font-extrabold leading-tight text-white">{title}</h2>}
          </div>
          {aside}
        </header>
      )}
      <div className={bodyClass}>{children}</div>
    </section>
  );
}

export function Chip({ tone = "muted", children, className = "" }) {
  const c = TONES[tone] || TONES.muted;
  return (
    <span className={`mono inline-flex items-center gap-1 rounded px-2 py-[3px] text-[11px] font-semibold uppercase tracking-wide ${className}`}
      style={{ color: c, border: `1px solid ${c}55`, background: `${c}18` }}>
      {children}
    </span>
  );
}

export function Btn({ variant = "ghost", className = "", ...p }) {
  const v = {
    mint: "bg-mint text-ink-950 hover:bg-mint-deep",
    ghost: "border border-ink-500 text-ink-100 hover:bg-ink-600",
    danger: "border border-[#F0525D66] text-[#F0525D] hover:bg-[#F0525D1A]",
  }[variant];
  return <button {...p} className={`inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-[13px] font-bold transition-colors disabled:opacity-50 ${v} ${className}`} />;
}

export function Kpi({ label, value, sub, tone = "mint" }) {
  return (
    <div className="panel p-4" style={{ borderTop: `2px solid ${TONES[tone]}` }}>
      <div className="eyebrow">{label}</div>
      <div className="mono mt-2 text-[28px] font-bold leading-none" style={{ color: TONES[tone] }}>{value}</div>
      <div className="mt-2 text-xs text-ink-300">{sub}</div>
    </div>
  );
}

export function Meter({ value = 0, max = 100, color = TONES.mint, height = 6 }) {
  const w = Math.min(Math.max((Number(value) / max) * 100, 0), 100);
  return (
    <div className="w-full overflow-hidden rounded-full bg-ink-600" style={{ height }}>
      <div className="h-full rounded-full" style={{ width: `${w}%`, background: color }} />
    </div>
  );
}

export function Empty({ title, children }) {
  return (
    <div className="rounded-lg border border-dashed border-ink-500 px-6 py-10 text-center">
      <p className="text-base font-bold text-ink-100">{title}</p>
      <p className="mx-auto mt-2 max-w-md text-sm text-ink-300">{children}</p>
    </div>
  );
}

export function OfflineBanner({ show }) {
  if (!show) return null;
  return (
    <div role="alert" className="mb-5 flex items-start gap-3 rounded-lg border border-[#F5A52466] bg-[#F5A52412] px-4 py-3 text-sm text-ink-100">
      <WifiOff size={18} className="mt-0.5 shrink-0 text-[#F5A524]" />
      <span>The LaneLogic API is not answering on port 8000. Start the backend (python start_backend.py). This page reconnects by itself.</span>
    </div>
  );
}

export const tipStyle = { background: "#0A1428", border: "1px solid #1C3156", borderRadius: 8, fontSize: 12, color: "#E4EAF5" };
