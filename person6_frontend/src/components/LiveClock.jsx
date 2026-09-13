import { useEffect, useState } from "react";

export default function LiveClock() {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const time = now.toLocaleTimeString("en-IN", { hour12: false });
  const date = now.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

  return (
    <div className="text-right leading-tight">
      <div className="font-mono text-sm text-slate-800 tabular-nums">{time}</div>
      <div className="text-[11px] text-slate-400">{date}</div>
    </div>
  );
}
