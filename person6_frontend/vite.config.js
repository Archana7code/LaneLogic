import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import fs from "node:fs";

// LaneLogic - PERSON 6: Frontend/Dashboard

/*
 * Serves Person 1's traffic videos and detections JSON to the dashboard, read-only,
 * without copying or changing anything inside person1_detection/.
 *   videos      : person1_detection/videos/*.mp4   (or person6_frontend/public/videos)
 *   detections  : person1_detection/output/*.json  (or person6_frontend/public/output)
 * URLs:  /media/index.json   /media/videos/<name>   /media/output/<name>
 */
const DIRS = {
  videos: [path.resolve(__dirname, "../person1_detection/videos"), path.resolve(__dirname, "public/videos")],
  output: [path.resolve(__dirname, "../person1_detection/output"), path.resolve(__dirname, "public/output")],
};
const TYPES = { ".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime", ".json": "application/json" };

function list(kind, exts) {
  const names = DIRS[kind].flatMap((d) => (fs.existsSync(d) ? fs.readdirSync(d) : []));
  return [...new Set(names)].filter((f) => exts.includes(path.extname(f).toLowerCase())).sort();
}

function laneMedia() {
  const handler = (req, res, next) => {
    if (!req.url || !req.url.startsWith("/media/")) return next();
    const url = decodeURIComponent(req.url.split("?")[0]);

    if (url === "/media/index.json") {
      res.setHeader("Content-Type", "application/json");
      return res.end(JSON.stringify({ videos: list("videos", [".mp4", ".webm", ".mov"]), outputs: list("output", [".json"]) }));
    }

    const m = url.match(/^\/media\/(videos|output)\/([^/\\]+)$/);
    if (!m || m[2].startsWith(".")) { res.statusCode = 404; return res.end("not found"); }
    const file = DIRS[m[1]].map((d) => path.join(d, m[2])).find((p) => fs.existsSync(p) && fs.statSync(p).isFile());
    if (!file) { res.statusCode = 404; return res.end("not found"); }

    const size = fs.statSync(file).size;
    const type = TYPES[path.extname(file).toLowerCase()] || "application/octet-stream";
    const range = req.headers.range; // needed so the video can be scrubbed
    if (range) {
      const [s, e] = range.replace(/bytes=/, "").split("-");
      const start = parseInt(s, 10) || 0;
      const end = e ? parseInt(e, 10) : size - 1;
      res.writeHead(206, { "Content-Range": `bytes ${start}-${end}/${size}`, "Accept-Ranges": "bytes", "Content-Length": end - start + 1, "Content-Type": type });
      return fs.createReadStream(file, { start, end }).pipe(res);
    }
    res.writeHead(200, { "Content-Length": size, "Content-Type": type, "Accept-Ranges": "bytes" });
    fs.createReadStream(file).pipe(res);
  };
  return {
    name: "lanelogic-media",
    configureServer(server) { server.middlewares.use(handler); },
    configurePreviewServer(server) { server.middlewares.use(handler); },
  };
}

export default defineConfig({
  plugins: [react(), laneMedia()],
  resolve: {
    alias: {
      // lets pages import Person 5's map component directly from the
      // sibling person5_gis folder without a messy relative path.
      "@person5": path.resolve(__dirname, "../person5_gis"),
    },
  },
  server: {
    port: 5173,
  },
});
