# LaneLogic frontend upgrade: run it, then push it safely

Only `person6_frontend/` is changed. Person 1 to Person 5 folders, `core/`, `tests/` and the root files are untouched.
No new npm packages were added, so `package.json` and `package-lock.json` are unchanged.

Commands are for Windows (cmd or PowerShell), because the repo uses `venv\Scripts` and `.bat` files.
Replace `C:\path\to\LaneLogic` with your real repo folder.

---------------------------------------------------------------------
## PART 1. Get your GitHub repo and add the new frontend (nothing else changes)

Repo: https://github.com/Archana7code/LaneLogic

The zip has no .git folder, so clone the repo fresh into a NEW location and copy only the frontend into it.

    cd C:\Users\YourName\Documents
    git clone https://github.com/Archana7code/LaneLogic.git LaneLogic_git
    cd LaneLogic_git
    git checkout -b frontend-redesign

Copy ONLY person6_frontend from the extracted zip (robocopy never deletes other files, and skips node_modules):

    robocopy "C:\path\to\extracted\LaneLogic-main\person6_frontend" "C:\Users\YourName\Documents\LaneLogic_git\person6_frontend" /E /XD node_modules

(robocopy exit codes 0 to 7 mean success.)

NOTE: the public repo currently has no core/, tests/, start_backend.py, run_closed_loop.py. Person 3's backend imports core/,
so to RUN the whole project, use the extracted zip folder (it has everything). Use LaneLogic_git only for pushing the frontend.

---------------------------------------------------------------------
## PART 2. Run everything (open 3 terminals, in this order)

### Terminal 1: backend (Person 3)

    cd C:\path\to\LaneLogic
    python -m venv venv
    venv\Scripts\activate
    pip install -r person3_backend\requirements.txt
    pip install requests
    python start_backend.py

Leave it running. Check: http://localhost:8000/docs opens.

### Terminal 2: put data into the backend

    cd C:\path\to\LaneLogic
    venv\Scripts\activate
    cd person5_gis
    python seed_roads.py --api http://localhost:8000
    python fake_data.py

That gives you roads plus 5 analysis windows for ROAD_001. For the full closed loop (events, alerts, chronic zones,
recommendations), run this from the repo root instead, after Person 1 has produced detections:

    cd C:\path\to\LaneLogic
    python run_closed_loop.py --api http://localhost:8000

### Terminal 3: frontend (Person 6)

    cd C:\path\to\LaneLogic\person6_frontend
    npm install
    npm run dev

Open http://localhost:5173

If the backend is on another port or machine, create `person6_frontend\.env` containing:

    VITE_API_BASE=http://localhost:8001

(`.env` is already in .gitignore, so it will not be pushed.)

Fresh database tip: on the Actions page, click "Generate actions for ..." to create recommendations from the UI.

---------------------------------------------------------------------
## PART 3. Push to git without changing anybody's file

    cd C:\Users\YourName\Documents\LaneLogic_git

1. See what changed:

       git status

2. PROOF that only frontend files changed. This must print nothing:

       git diff --name-only | findstr /v /b "person6_frontend/"

   (Mac/Linux: `git diff --name-only | grep -v '^person6_frontend/'`)
   If a line appears, undo that file with `git checkout -- <that file>`.

3. Stage ONLY the frontend folder (never use `git add .`):

       git add person6_frontend
       git status

   Everything under "Changes to be committed" should start with person6_frontend/.

4. Commit and push to your own branch, not main:

       git commit -m "Redesign frontend: lane cross-section UI, alerts, actions, simulation"
       git push -u origin frontend-redesign

5. On GitHub, click "Compare & pull request" and let a teammate review before merging.

Safety notes
- Your teammates' work stays safe because you only push a branch.
- If push is rejected: `git pull --rebase origin main` then push again.
- To go back at any time: `git checkout main`. Nothing on main changes.

---------------------------------------------------------------------
## VIDEO WITH DETECTION BOXES (Live Monitoring page)

The Live Monitoring page plays the source video and draws the YOLO + ByteTrack boxes on top of it
(green = moving, red = parked with seconds, amber = waiting). The boxes come from Person 1's detections JSON,
drawn in the browser. No Person 1 file is changed.

Files it looks for (matched by number: ROAD_001 -> 1, ROAD_002 -> 2, ...):

    person1_detection\videos\traffic1.mp4         (source video)
    person1_detection\output\detections1.json     (made by Person 1's detector)

Make the detections file (from repo root, venv active; drop --show so it does not open a window):

    venv\Scripts\activate
    pip install -r person1_detection\requirements.txt
    cd person1_detection
    python main.py --source videos\traffic1.mp4 --model yolov8s.pt --output output\detections1.json --csv output\detections1.csv --phase-seconds 5 --phase-output output\detection_stream_1.jsonl --road-id ROAD_001 --road-name "Noida" --source-name "traffic1.mp4" --clear-phase-output

Repeat with traffic2.mp4 / ROAD_002 / detections2.json etc. for other roads.
Then restart `npm run dev` (or just refresh) and open Live Monitoring, pick the road.

Already have the files somewhere else? On the page use "Load video" and "Load detections.json" to pick them by hand.

Notes
- .mp4 files and output\ are in .gitignore, so they are NOT pushed to GitHub. Each teammate keeps them locally.
- Video must be .mp4 (H.264) to play in Chrome/Edge.

---------------------------------------------------------------------
## SEE EVERY FEATURE WITHOUT VIDEOS (demo data)

With the backend running (Terminal 1), from the repo root in a NEW terminal:

    cd C:\path\to\LaneLogic-main
    venv\Scripts\activate
    python person6_frontend\demo_seed.py

It only talks to the backend API (roads, analysis, events, chronic zones, recommendations, one outcome).
All records are tagged DEMO. Run it once on a fresh database; running again may duplicate analysis windows.
Then refresh http://localhost:5173.

## MAP

The map uses free OpenStreetMap / Esri tiles (no API key). Use the Dark / Street / Satellite switch on the map.
(CARTO dark tiles now need a key, which caused the "API KEY REQUIRED" watermark.)
