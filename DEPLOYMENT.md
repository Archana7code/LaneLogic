# LaneLogic Prototype Deployment Guide

This guide describes how to deploy the current LaneLogic prototype to [Render](https://render.com/).

## 1. Architecture

- **Backend:** FastAPI (Python) web service exposing the LaneLogic APIs.
- **Frontend:** React/Vite Single Page Application (SPA) statically hosted.
- **Database:** Local SQLite database (persisted via Render Disk, or ephemeral without one).
- **Media/Video:** For the prototype demo, deterministic synthetic data and statically bundled media are used to avoid large video processing overhead.

## 2. Environment Variables

### Backend (`person3_backend/.env`)
- `FRONTEND_ORIGIN`: The URL of your deployed frontend (e.g., `https://lanelogic-frontend.onrender.com`) to restrict CORS. Use `*` during initial testing.
- `DATABASE_URL`: The SQLite connection string. Defaults to `sqlite:///./lanelogic.db`. For persistent storage, set it to `sqlite:////data/lanelogic.db` (if you've mounted a Render Disk to `/data`).

### Frontend (`person6_frontend/.env`)
- `VITE_API_URL`: The URL of your deployed backend (e.g., `https://lanelogic-backend.onrender.com`).

*Example `.env.example` files are provided in both directories.*

## 3. Deployment Instructions

### Automatic Deployment (Recommended)
You can deploy both services using the provided `render.yaml` Blueprint.

1. Push your repository to GitHub.
2. In the Render Dashboard, go to **Blueprints** -> **New Blueprint Instance**.
3. Connect your GitHub repository.
4. Render will automatically detect and create both the `lanelogic-backend` and `lanelogic-frontend` services.
5. After deployment, update the Environment Variables in the Render Dashboard:
   - For the frontend, set `VITE_API_URL` to the actual URL of the deployed backend.
   - For the backend, set `FRONTEND_ORIGIN` to the actual URL of the deployed frontend.

### Manual Deployment

#### Backend Service
1. **Type:** Web Service
2. **Environment:** Python
3. **Root Directory:** `person3_backend`
4. **Build Command:** `pip install -r requirements.txt`
5. **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. **Environment Variables:** `FRONTEND_ORIGIN` (set to `*` initially or the frontend URL)

#### Frontend Static Site
1. **Type:** Static Site
2. **Root Directory:** `person6_frontend`
3. **Build Command:** `npm install && npm run build`
4. **Publish Directory:** `dist`
5. **Environment Variables:** `VITE_API_URL` (set to the backend URL)

*(Note: The SPA routing is handled by the `_redirects` file automatically included in the build).*

## 4. Database Strategy

The prototype uses **SQLite**.
- **Without a Disk:** The database will reset every time the backend redeploys. This is perfectly fine for the prototype.
- **With a Disk (Paid feature):** You can mount a Render Disk to `/data` in the backend service configuration and set `DATABASE_URL=sqlite:////data/lanelogic.db` to persist the data.

## 5. Media & Video Strategy

The prototype demo relies on synthetic telemetry seeded via `demo_seed.py`. 
For a production application, actual media processing (Person 1) should be deployed as a separate offline background worker rather than integrated directly into the web API endpoint to prevent request timeouts.

## 6. Seeding Demo Data

Once the backend is deployed, you must seed it with demo data. From your local machine, run:

```bash
python person6_frontend/demo_seed.py --api https://<your-backend-name>.onrender.com
```

This will populate the backend with deterministic demonstration events, analysis windows, and recommendations.

## 7. Health Checks

The backend includes a health endpoint to verify the service is running:
```
GET https://<your-backend-name>.onrender.com/health
```

## 8. Known Pre-existing Analytical Limitations

*These are existing limitations in the application logic, documented for awareness:*
- Multiple analytical sources of truth (e.g., phase-local observation identities).
- Road-space measurement inconsistency.
- Fabricated/default confidence and recurrence inputs in early pipelines.
- Insufficient historical recurrence baseline in some metrics.
- Multiple severity definitions across modules.
- First-event cause classification biases.
- Simulation baseline constraints and incomplete continuous learning loops.

## 9. Local Setup After Deployment

If you want to continue running the application locally:
1. Backend: `cd person3_backend` and `uvicorn main:app --reload`
2. Frontend: `cd person6_frontend` and `npm run dev` (it will default to `http://localhost:8000` for the API).
