# LaneLogic — SIH 2026

Intelligent road/traffic monitoring and problem-analysis system.
Video/camera → detection & tracking → space & cause analysis → backend →
recurrence & recommendations → GIS map → dashboard.

All technology is free/local: YOLOv8 (Ultralytics), OpenCV, ByteTrack,
FastAPI + SQLite, React + Vite + Tailwind, Leaflet + OpenStreetMap.
No paid APIs are used anywhere.

## Folder ownership

| Folder | Owner | Responsibility |
|---|---|---|
| `person1_detection/` | Person 1 | YOLOv8 + ByteTrack vehicle detection & tracking |
| `person2_analysis/` | Person 2 | Road-space occupancy + rule-based cause analysis |
| `person3_backend/` | Person 3 | FastAPI + SQLite API connecting every module |
| `person4_recommendation/` | Person 4 | Chronic-zone detection + intervention recommendations |
| `person5_gis/` | Person 5 | Leaflet/OpenStreetMap map component |
| `person6_frontend/` | Person 6 | React + Vite + Tailwind dashboard (final integration) |

## Run order (demo)

1. **Backend first** (everything else talks to it):
   ```
   cd person3_backend
   pip install -r requirements.txt
   uvicorn main:app --reload --port 8000
   ```

2. **Seed demo road metadata** (so the map/dashboard have something to show):
   ```
   cd person5_gis
   pip install -r requirements.txt   # only 'requests' needed here
   python seed_roads.py --api http://localhost:8000
   ```

3. **Detection & tracking** on a sample video or webcam:
   ```
   cd person1_detection
   pip install -r requirements.txt
   python main.py --source ../sample_traffic.mp4 --output detections.json --show
   ```

4. **Space & cause analysis** on Person 1's output:
   ```
   cd person2_analysis
   pip install -r requirements.txt
   python main.py --detections ../person1_detection/detections.json \
                   --roi roi_config.json --output analysis.json
   ```
   Then POST `analysis.json`'s contents (wrapped as `{"observations": [...]}`)
   to the backend's `/analysis/bulk` endpoint — either with a small script or
   via `curl`/Postman during the demo. Repeat steps 3-4 across a few short
   clips so Person 4 has enough historical windows to work with.

5. **Recurrence & recommendations**, once several observation windows exist:
   ```
   cd person4_recommendation
   pip install -r requirements.txt
   python main.py --api http://localhost:8000
   ```

6. **Dashboard**:
   ```
   cd person6_frontend
   npm install
   npm run dev
   ```
   Open the printed local URL (default `http://localhost:5173`) and walk
   through: Live Monitoring → Problem Analysis → History/Chronic Zones →
   Recommendations → GIS Map.

## Notes for the demo

- Every "cause" and "recommendation" is produced by transparent, rule-based
  logic with fixed, documented thresholds — not a trained ML model. This is
  intentional: there is no labeled dataset for causes/interventions, and an
  explainable rule set is safer to demo and defend during judging than an
  invented accuracy number.
- The vehicle detector/tracker (Person 1) is the only ML component, and it
  uses YOLOv8's standard pretrained COCO weights plus ByteTrack — no custom
  training required for the prototype.
- Status colors (green/yellow/red) and the chronic-zone threshold are all
  simple constants at the top of `person3_backend/main.py` and
  `person4_recommendation/main.py` so they're easy to tune live if a judge
  asks "why is this road red?".
