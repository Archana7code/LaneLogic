import { useEffect, useRef, useState } from "react";
import { Film, Upload, FileJson } from "lucide-react";
import { Chip } from "./ui";
import { API_BASE } from "../api";

/*
 * Plays the source traffic video and draws Person 1's YOLO + ByteTrack boxes on top of it,
 * frame-synced from detections.json. Nothing is rendered on the server; the boxes are drawn
 * in the browser from the recorded detections.
 */
const REF_W = 960; // Person 1 resizes frames to at most 960 px wide before detecting
const COLORS = { moving: "#2DDBA0", parked: "#F0525D", signal_waiting: "#F5A524", stationary: "#F5A524" };
const numOf = (s) => { const m = String(s || "").match(/(\d+)/); return m ? parseInt(m[1], 10) : null; };

export default function VideoDetectionPlayer({ roadId }) {
  const vref = useRef(null);
  const cref = useRef(null);
  const idx = useRef({ times: [], frames: [] });
  const [manifest, setManifest] = useState({ videos: [], outputs: [] });
  const [videoUrl, setVideoUrl] = useState(null);
  const [videoName, setVideoName] = useState("");
  const [detName, setDetName] = useState("");
  const [total, setTotal] = useState(0);
  const [live, setLive] = useState({ moving: 0, parked: 0, waiting: 0 });
  const [note, setNote] = useState("");

  function indexDetections(data, name) {
    const rows = Array.isArray(data) ? data : data?.detections || [];
    const map = new Map();
    rows.forEach((d) => {
      const t = Number(d.timestamp);
      if (!Number.isFinite(t) || !Array.isArray(d.bbox)) return;
      const k = t.toFixed(3);
      if (!map.has(k)) map.set(k, []);
      map.get(k).push(d);
    });
    const times = [...map.keys()].map(Number).sort((a, b) => a - b);
    idx.current = { times, frames: times.map((t) => map.get(t.toFixed(3))) };
    setTotal(rows.length);
    setDetName(name);
    setNote(rows.length ? "" : "That file has no detections in the expected format.");
  }

  function clearDetections() { idx.current = { times: [], frames: [] }; setTotal(0); setDetName(""); }

  useEffect(() => {
    fetch("/media/index.json").then((r) => r.json()).then(setManifest).catch(() => {});
  }, []);

  // pick the matching video and detections for the selected road (ROAD_001 -> traffic1.mp4 + detections1.json)
  useEffect(() => {
    const n = numOf(roadId);
    const v = manifest.videos.find((x) => numOf(x) === n);
    const o = manifest.outputs.find((x) => /detection/i.test(x) && numOf(x) === n);
    // Demo fallback: ROAD_001 → /videos/traffic1.mp4 (served from public/ on Render)
    setVideoUrl(v ? `/media/videos/${encodeURIComponent(v)}` : (roadId === "ROAD_001" ? "/videos/traffic1.mp4" : null));
    setVideoName(v || "");
    clearDetections();
    if (o) {
      fetch(`/media/output/${encodeURIComponent(o)}`).then((r) => r.json()).then((d) => indexDetections(d, o)).catch(() => setNote("Could not read the detections file."));
    }
  }, [roadId, manifest]);

  // draw boxes for whatever frame the video is on
  useEffect(() => {
    let raf, last = "";
    const frameAt = (t) => {
      const { times, frames } = idx.current;
      if (!times.length) return [];
      let lo = 0, hi = times.length - 1, best = -1;
      while (lo <= hi) { const mid = (lo + hi) >> 1; if (times[mid] <= t + 0.02) { best = mid; lo = mid + 1; } else hi = mid - 1; }
      return best < 0 || t - times[best] > 1 ? [] : frames[best];
    };
    const loop = () => {
      const v = vref.current, c = cref.current;
      if (v && c && v.videoWidth) {
        const w = v.clientWidth, h = v.clientHeight;
        if (c.width !== w || c.height !== h) { c.width = w; c.height = h; }
        const ctx = c.getContext("2d");
        ctx.clearRect(0, 0, w, h);
        const refW = Math.min(v.videoWidth, REF_W);
        const sx = w / refW, sy = h / (v.videoHeight * (refW / v.videoWidth));
        let m = 0, p = 0, wt = 0;
        ctx.font = "600 11px 'JetBrains Mono', monospace";
        frameAt(v.currentTime).forEach((d) => {
          const st = d.movement_state;
          if (st === "moving") m++; else if (st === "parked") p++; else wt++;
          const col = COLORS[st] || "#38C6F4";
          const [x1, y1, x2, y2] = d.bbox;
          const X = x1 * sx, Y = y1 * sy, W = (x2 - x1) * sx, H = (y2 - y1) * sy;
          ctx.lineWidth = st === "parked" ? 3 : 2;
          ctx.fillStyle = col + "26"; ctx.fillRect(X, Y, W, H);
          ctx.strokeStyle = col; ctx.strokeRect(X, Y, W, H);
          const label = `#${d.vehicle_id} ${String(d.vehicle_type).toUpperCase()}` +
            (st === "parked" ? ` PARKED ${Math.round(d.stationary_duration || 0)}s` : st === "signal_waiting" ? " WAITING" : "");
          const tw = ctx.measureText(label).width + 10, ly = Math.max(Y - 16, 0);
          ctx.fillStyle = col; ctx.fillRect(X, ly, tw, 16);
          ctx.fillStyle = "#060D1B"; ctx.fillText(label, X + 5, ly + 12);
        });
        const key = `${m}/${p}/${wt}`;
        if (key !== last) { last = key; setLive({ moving: m, parked: p, waiting: wt }); }
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, []);

  async function pickVideo(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    setVideoUrl(URL.createObjectURL(f)); 
    setVideoName(f.name);
    setNote("Uploading and processing video...");

    const formData = new FormData();
    formData.append("video", f);
    formData.append("road_id", roadId);

    try {
      const res = await fetch(`${API_BASE}/process-video`, {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        setNote("Pipeline processing... Phase outputs will appear automatically. Note: Box rendering requires detections.json which is generated at the end, or you can load it manually.");
      } else {
        setNote("Failed to start processing on backend.");
      }
    } catch (err) {
      console.error(err);
      setNote("Error starting pipeline on backend. Make sure the local backend is running (python start_backend.py).");
    }
  }
  function pickJson(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    f.text().then((t) => indexDetections(JSON.parse(t), f.name)).catch(() => setNote("That file is not valid JSON."));
  }

  const btn = "inline-flex cursor-pointer items-center gap-2 rounded-md border border-ink-500 px-3 py-2 text-[13px] font-bold text-ink-100 hover:bg-ink-600";

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <Chip tone="cyan"><Film size={12} /> YOLO + ByteTrack replay</Chip>
        {videoName && <span className="mono text-xs text-ink-300">{videoName}</span>}
        {detName && <span className="mono text-xs text-ink-300">· {detName} · {total} detections</span>}
      </div>

      <div className="relative overflow-hidden rounded-lg bg-black ring-1 ring-ink-600">
        {videoUrl ? (
          <>
            <video key={videoUrl} ref={vref} src={videoUrl} className="block w-full" controls muted loop autoPlay playsInline
              onError={() => setNote("This video could not be played. Try an .mp4 (H.264).")} />
            <canvas ref={cref} className="pointer-events-none absolute left-0 top-0 h-full w-full" />
          </>
        ) : (
          <div className="flex min-h-[260px] flex-col items-center justify-center gap-2 px-6 py-10 text-center">
            <Film className="text-ink-400" size={32} />
            <p className="text-base font-bold text-ink-100">No video found for this road yet</p>
            <p className="max-w-lg text-sm text-ink-300">
              Put the source video in <span className="mono text-mint">person1_detection/videos/</span> (for example traffic1.mp4 for ROAD_001)
              and the matching <span className="mono text-mint">detections1.json</span> in <span className="mono text-mint">person1_detection/output/</span>,
              then refresh. Or load them by hand below.
            </p>
          </div>
        )}
      </div>

      <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-2">
          <Chip tone="mint">Moving {live.moving}</Chip>
          <Chip tone="red">Parked {live.parked}</Chip>
          <Chip tone="amber">Waiting {live.waiting}</Chip>
        </div>
        <div className="flex flex-wrap gap-2">
          <label className={btn}><Upload size={14} /> Load video<input type="file" accept="video/*" className="hidden" onChange={pickVideo} /></label>
          <label className={btn}><FileJson size={14} /> Load detections.json<input type="file" accept=".json,application/json" className="hidden" onChange={pickJson} /></label>
        </div>
      </div>
      {videoUrl && total === 0 && !note && (
        <p className="mt-2 text-xs text-ink-300">Video is playing, but no detections file is loaded for it yet, so no boxes are drawn. Put detectionsN.json in person1_detection/output/ or use Load detections.json.</p>
      )}
      {note && <p role="alert" className="mt-2 text-xs text-[#F5A524]">{note}</p>}
    </div>
  );
}









