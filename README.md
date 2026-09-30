# 🚦 LaneLogic

### AI-Powered Traffic Intelligence & Road Obstruction Analysis System

LaneLogic is an AI-powered traffic intelligence platform that transforms road video into **vehicle detections, obstruction events, road-space insights, historical patterns, and actionable recommendations**.

Built for **Smart India Hackathon 2026**, LaneLogic combines computer vision, multi-object tracking, geometric analysis, rule-based reasoning, historical analysis, GIS visualization, and decision-support logic to help understand why road space is being lost and what interventions can be considered.

> **LaneLogic goes beyond vehicle detection — it analyzes movement, duration, road impact, context, and historical patterns to turn traffic video into actionable road intelligence.**

---

# 🌍 Problem Statement

Urban roads lose usable capacity not only because of overall traffic volume, but also because of localized and recurring obstructions such as:

- Illegal or temporary parking
- Loading and unloading activity
- School-zone drop-offs
- Signal-based vehicle queues
- Localized congestion
- Recurring obstruction hotspots

Traditional traffic monitoring systems primarily answer:

> **"What vehicles are present?"**

LaneLogic aims to answer:

> **"What is happening?"**  
> **"How is road space being affected?"**  
> **"What is the likely cause?"**  
> **"Does the problem recur?"**  
> **"What intervention can be considered?"**

---

# 🎯 Objective

The objective of LaneLogic is to build an evidence-driven pipeline that converts traffic video into structured road intelligence.

The system follows:

```text
Video
  ↓
Vehicle Detection
  ↓
Multi-Object Tracking
  ↓
Movement Analysis
  ↓
Obstruction Event
  ↓
Road-Space & Severity Analysis
  ↓
Cause Classification
  ↓
Historical Recurrence
  ↓
Recommendation
  ↓
GIS / Dashboard
  ↓
Feedback & Outcomes
```

---

# 🧠 Key Features

## 🚗 1. Vehicle Detection & Tracking

LaneLogic uses:

- **YOLOv8** for object detection
- **ByteTrack** for multi-object tracking
- **OpenCV** for video processing
- Track histories for movement analysis

The detection pipeline extracts:

- Vehicle class
- Bounding box
- Track ID
- Position
- Movement history
- Stationary duration
- Temporal observations

The current implementation uses a YOLOv8 model with the available COCO vehicle classes.

A specialized Indian-road detection model is planned as a future enhancement.

---

# 🚧 2. Obstruction Detection

Not every stationary vehicle represents an obstruction.

LaneLogic analyzes vehicle behavior using:

- Movement
- Stationary duration
- Spatial position
- Road/ROI context
- Traffic conditions
- Temporal behavior

The system is designed around a **canonical obstruction-event lifecycle**, allowing downstream components to work with a consistent event representation.

---

# 📊 3. Road-Space Intelligence

LaneLogic analyzes vehicle interaction with configured road regions.

Current capabilities include:

- ROI-based occupancy analysis
- Blocked-space estimation
- Vehicle concentration
- Road-space impact
- Severity assessment
- Traffic-window analysis

### Current Measurement Approach

The current implementation primarily uses **image-space / ROI-based geometry**.

Therefore, current road-space values should be interpreted as analytical estimates rather than fully calibrated physical measurements.

Future development includes:

- Camera calibration
- Perspective transformation / homography
- Physical road-width estimation
- Calibrated occupied-width measurement
- Measurement-quality metadata

---

# 🧩 4. Explainable Cause Classification

LaneLogic uses transparent, rule-based reasoning to identify potential obstruction causes.

Current cause categories include:

```text
traffic_signal_queue
loading_unloading
school_dropoff
illegal_parking
general_congestion
normal / unclassified
```

Classification uses contextual information such as:

- Stationary duration
- Vehicle movement
- Spatial location
- Queue characteristics
- Time-of-day conditions
- Configured road zones

> **Transparency:** Cause classification is currently rule-based. Its confidence/evidence score should not be interpreted as a calibrated machine-learning probability.

A trained ML-based cause classifier is planned for a future version after obtaining an appropriate labeled dataset.

---

# 🔁 5. Historical Recurrence Analysis

LaneLogic analyzes historical observations to identify repeated obstruction patterns.

The recurrence analysis considers:

- Total events
- Observation period
- Event frequency
- Days with observed problems
- Temporal consistency
- Spatial consistency
- Vehicle distribution
- Obstruction duration

This supports identification of:

- Recurring problem areas
- Time-specific patterns
- Repeated obstruction zones
- Potential chronic hotspots

> **Important:** Chronicity requires sufficient historical evidence. When adequate multi-day observations are unavailable, the system should report insufficient evidence rather than treating a single observation as a chronic problem.

---

# 💡 6. Recommendation Engine

LaneLogic converts analytical evidence into intervention recommendations.

The decision flow is:

```text
Problem
   ↓
Evidence
   ↓
Cause
   ↓
Severity / Road Impact
   ↓
Historical Recurrence
   ↓
Candidate Interventions
   ↓
Intervention Scoring
   ↓
Recommendation
```

Potential intervention categories include:

- Parking enforcement
- Loading/unloading management
- School-zone traffic management
- Traffic-control measures
- Signage or lane-management measures
- Targeted monitoring

The recommendation engine is designed as a **decision-support system for authorities**, not as an autonomous authority decision-maker.

---

# 🗺️ 7. GIS & Road Intelligence

LaneLogic provides geographic visualization of monitored road corridors and identified problem areas.

The GIS layer supports:

- Road/corridor visualization
- Problem-zone visualization
- Chronic-zone visualization
- Severity indicators
- Road-level insights
- Intervention context

The current dashboard uses configured road information and analytical results for visualization.

Future versions can incorporate more detailed GIS geometries and calibrated road boundaries.

---

# 🔄 8. Feedback & Intervention Outcomes

LaneLogic includes infrastructure for recording feedback and intervention outcomes.

The intended workflow is:

```text
Recommendation
      ↓
Authority Action
      ↓
Intervention Outcome
      ↓
Feedback
      ↓
Historical Evidence
```

The system can preserve information related to:

- Human feedback
- Recommended interventions
- Intervention outcomes
- Before/after observations
- Model/version information

> The current implementation provides the foundation for a closed-loop workflow. It does **not** claim autonomous continuous ML retraining.

---

# 🏗️ Architecture

LaneLogic is organized into modular components.

| Module | Responsibility |
|---|---|
| **Person 1** | Vehicle detection and multi-object tracking |
| **Person 2** | Road-space, movement, severity and cause analysis |
| **Person 3** | Backend API, database and persistence |
| **Person 4** | Historical recurrence and recommendation logic |
| **Person 5** | GIS / road intelligence |
| **Person 6** | Frontend dashboard and visualization |
| **Core** | Shared event, geometry, cause, recurrence, intervention, outcome and simulation logic |

---

# 🔗 Canonical Data Flow

The intended integrated architecture is:

```text
                    ┌────────────────────┐
                    │    Traffic Video   │
                    └─────────┬──────────┘
                              ↓
                    ┌────────────────────┐
                    │ YOLOv8 + ByteTrack │
                    │     Person 1       │
                    └─────────┬──────────┘
                              ↓
                    ┌────────────────────┐
                    │ Canonical Vehicle  │
                    │    Detections      │
                    └─────────┬──────────┘
                              ↓
                    ┌────────────────────┐
                    │ Obstruction Event  │
                    │     Analysis       │
                    └─────────┬──────────┘
                              ↓
                    ┌────────────────────┐
                    │ Road-Space &       │
                    │ Severity Analysis  │
                    └─────────┬──────────┘
                              ↓
                    ┌────────────────────┐
                    │ Cause              │
                    │ Classification     │
                    └─────────┬──────────┘
                              ↓
                    ┌────────────────────┐
                    │ Historical         │
                    │ Recurrence         │
                    └─────────┬──────────┘
                              ↓
                    ┌────────────────────┐
                    │ Recommendation     │
                    │ Decision Engine    │
                    └─────────┬──────────┘
                              ↓
                    ┌────────────────────┐
                    │ GIS / Dashboard    │
                    └─────────┬──────────┘
                              ↓
                    ┌────────────────────┐
                    │ Feedback /         │
                    │ Outcomes           │
                    └────────────────────┘
```

---

# 🧱 Project Structure

```text
LaneLogic/
│
├── person1_detection/
│   ├── main.py
│   ├── annotate.py
│   ├── requirements.txt
│   ├── run_all_videos.bat
│   └── ...
│
├── person2_analysis/
│   ├── ...
│   └── roi_config.json
│
├── person3_backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   └── ...
│
├── person4_recommendation/
│   ├── ...
│
├── person6_frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── ...
│
├── core/
│   ├── event_engine.py
│   ├── generate_events.py
│   ├── geometry.py
│   ├── cause_classifier.py
│   ├── recurrence.py
│   ├── interventions.py
│   ├── outcomes.py
│   ├── simulation.py
│   ├── alerts.py
│   └── continuous_learning.py
│
├── tests/
│
├── render.yaml
├── run_closed_loop.py
├── start_backend.py
├── DEPLOYMENT.md
└── README.md
```

---

# 🛠️ Technology Stack

## Computer Vision

- Python
- YOLOv8
- Ultralytics
- OpenCV
- ByteTrack

## Data & Analysis

- NumPy
- Pandas
- Shapely
- Rule-based analytical models

## Backend

- FastAPI
- SQLAlchemy
- Pydantic
- SQLite

## Frontend

- React
- Vite
- JavaScript
- CSS
- GIS/map visualization

## Development & Testing

- Git
- GitHub
- VS Code
- Pytest

## Deployment

- Render
- Separate frontend and backend services

---

# ⚡ Local Setup

## 1. Clone the Repository

```bash
git clone https://github.com/Archana7code/LaneLogic.git
cd LaneLogic
```

---

## 2. Create a Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python -m venv venv
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r person1_detection/requirements.txt
pip install -r person2_analysis/requirements.txt
pip install -r person3_backend/requirements.txt
pip install -r person4_recommendation/requirements.txt
```

For the frontend:

```bash
cd person6_frontend
npm install
cd ..
```

---

# ▶️ Running the Backend

From the project root:

```bash
python start_backend.py
```

The backend runs locally at:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/health
```

---

# 🎥 Video Processing

LaneLogic is designed around an automated processing pipeline:

```text
Video
  ↓
Person 1
  ↓
YOLOv8 + ByteTrack
  ↓
Detection Stream
  ↓
Person 2
  ↓
Analysis
  ↓
Person 3
  ↓
Database
  ↓
Person 4
  ↓
Recommendations
  ↓
Person 6
  ↓
Dashboard
```

Intermediate detection and analysis files are internal pipeline artifacts.

For development and debugging, individual processing stages can be executed separately.

The production workflow is being extended toward direct video submission, where the system automatically invokes the detection and analysis stages without requiring the user to manually provide intermediate JSON/JSONL files.

---

# 🖥️ Frontend

Start the React development server:

```bash
cd person6_frontend
npm run dev
```

The frontend provides:

- Live monitoring
- Road intelligence
- Problem analysis
- Intervention recommendations
- Alerts
- Road-level statistics
- Obstruction events
- GIS visualization

---

# 🌐 Deployment Architecture

LaneLogic uses a separated frontend/backend architecture.

```text
                 ┌──────────────────────┐
                 │ React Frontend       │
                 │ Person 6             │
                 └──────────┬───────────┘
                            │
                            ↓
                 ┌──────────────────────┐
                 │ FastAPI Backend      │
                 │ Person 3             │
                 └──────────┬───────────┘
                            │
                            ↓
                 ┌──────────────────────┐
                 │ Database / Analysis  │
                 └──────────────────────┘
```

Production API configuration uses environment variables.

### Frontend

```text
VITE_API_URL
```

### Backend

```text
FRONTEND_ORIGIN
DATABASE_URL
```

Production video processing should not depend on the frontend service's local filesystem.

For scalable processing, the architecture can be extended to:

```text
Frontend
   ↓
API
   ↓
Processing Job
   ↓
Worker
   ↓
Person 1
   ↓
Person 2
   ↓
Database
   ↓
Recommendations
   ↓
Frontend
```

---

# 📊 Current Implementation Status

| Component | Status |
|---|---|
| YOLOv8 Detection | ✅ Working |
| ByteTrack Tracking | ✅ Working |
| Movement Analysis | ✅ Working |
| Obstruction Analysis | ✅ Working |
| Road-Space Analysis | 🟡 ROI / image-space based |
| Severity Analysis | ✅ Rule-based |
| Cause Classification | ✅ Rule-based |
| Historical Recurrence | 🟡 Functional; historical hardening ongoing |
| Recommendation Engine | ✅ Integrated |
| Backend API | ✅ Functional |
| Database Persistence | ✅ Functional |
| GIS / Road Intelligence | ✅ Integrated |
| React Dashboard | ✅ Integrated |
| Alerts | ✅ Integrated |
| Feedback / Outcomes | 🟡 Infrastructure available |
| Automatic Video-to-Analysis Workflow | 🟡 Integration in progress |
| Calibrated Physical Road Measurement | 🔄 Planned |
| ML-Based Cause Classification | 🔄 Planned |
| Controlled Continuous Model Learning | 🔄 Planned |

---

# ⚠️ Current Limitations

### 1. Road-Space Calibration

Current road-space analysis primarily uses ROI/image-space geometry.

Accurate physical measurements require camera calibration and perspective transformation.

### 2. Cause Classification

Cause classification is currently rule-based and is not trained on a labeled cause-classification dataset.

### 3. Historical Recurrence

Reliable chronicity requires sufficient historical observations, preferably across multiple days.

### 4. Detection Classes

The current detector depends on the configured YOLO model and its available classes.

Specialized Indian-road objects may require a custom-trained detector.

### 5. Continuous Learning

The project contains feedback and outcome infrastructure but does not currently claim autonomous continuous ML retraining.

### 6. Production Video Processing

YOLO-based processing requires appropriate compute and storage.

For scalable deployment, video processing should be separated from the frontend service through a dedicated processing worker or equivalent architecture.

---

# 🧪 Testing

Tests are maintained under:

```text
tests/
```

Run:

```bash
pytest
```

Important integration tests should cover:

- Detection generation
- Tracking
- Obstruction event generation
- Event identity
- Backend persistence
- Recommendation generation
- Recurrence analysis
- Frontend/backend communication
- End-to-end video processing

---

# 🚀 Roadmap

## Phase 1 — Pipeline Hardening

- Canonical obstruction-event lifecycle
- Deterministic event identity
- Idempotent processing
- Unified road-space measurement
- Consistent event schemas
- Multi-day recurrence evidence

## Phase 2 — Decision Intelligence

- Standardized severity taxonomy
- Evidence-backed recommendations
- Improved cause aggregation
- Authority feedback
- Intervention outcome tracking

## Phase 3 — Production Processing

- Automatic video upload
- Processing jobs
- Background workers
- YOLO + ByteTrack execution
- Automatic Person 2 handoff
- Processing-status monitoring
- Robust production storage

## Phase 4 — Advanced Intelligence

- Camera calibration
- Homography-based physical measurement
- Indian-road-specific detection model
- ML-based cause classification
- Controlled model evaluation and retraining
- Real-time / RTSP processing

---

# 🎯 Smart India Hackathon 2026

**Project:** LaneLogic

**Event:** Smart India Hackathon 2026

**Domain:** Smart Traffic / Intelligent Transportation

### Problem Focus

LaneLogic focuses on identifying and understanding road-space inefficiencies caused by vehicle behavior, temporary obstruction, localized congestion, and recurring traffic patterns.

### Proposed Value

Instead of providing only vehicle counts, LaneLogic builds an evidence chain:

```text
Vehicle
   ↓
Movement
   ↓
Obstruction
   ↓
Road Impact
   ↓
Cause
   ↓
Historical Pattern
   ↓
Intervention
```

This enables traffic authorities and urban planners to move from simple observation toward **evidence-based decision support**.

---

# 🔐 Design Principles

## One Analytical Source of Truth

Downstream modules should consume canonical detections and obstruction events rather than creating competing versions of the same event.

## Evidence Before Recommendation

Recommendations should use measurable observations, cause evidence, road impact, and historical information.

## Transparent Reasoning

Rule-based decisions should remain explainable and clearly distinguishable from probabilistic ML predictions.

## Honest Uncertainty

When sufficient evidence is unavailable, the system should report that limitation instead of fabricating confidence or recurrence.

## Modular Architecture

Detection, analysis, persistence, recommendation, GIS, and frontend components remain independently testable and replaceable.

---

# 🌟 Vision

LaneLogic aims to evolve into a city-scale road intelligence platform capable of helping authorities understand:

- **Where** road capacity is being lost
- **Why** the obstruction occurs
- **When** it occurs
- **Whether** it is recurring
- **What** intervention can be considered
- **Whether** an intervention produced a measurable outcome

The long-term vision is to transform raw traffic video into a structured evidence chain for **data-driven urban mobility and road management**.

---

# 🚦 LaneLogic

### Detect. Explain. Analyze. Recommend.

**From traffic video to road intelligence.**
