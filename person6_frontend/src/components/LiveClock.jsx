import { useEffect, useState } from "react";

export default function LiveClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => { const id = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(id); }, []);
  return (
    <div className="hidden text-right leading-tight md:block">
      <div className="mono text-sm font-semibold text-white">{now.toLocaleTimeString("en-IN", { hour12: false })}</div>
      <div className="text-[11px] text-ink-300">{now.toLocaleDateString("en-IN", { weekday: "short", day: "2-digit", month: "short" })}</div>
    </div>
  );
}
