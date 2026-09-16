# RailCast — Dynamic ETA Intelligence Demo

A working SIH demo based on the Rail Cast presentation for **SIH26028 — Dynamic Forecast of Expected Time of Arrival (ETA) for Coaching Trains**.

## What works
- FastAPI backend with REST endpoints.
- WebSocket-based live updates every 5 seconds.
- Search and select trains.
- Dynamic ETA, delay, confidence and reason generation.
- Interactive Leaflet/OpenStreetMap route map.
- Live movement simulation, congestion and weather factors.
- Overview, Live Tracking, Analytics and Delay Alerts screens.
- Responsive layout for laptop/tablet/mobile.

## Run locally
Requires Python 3.10+.

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000`.

## Important hackathon note
This demo uses simulated train/GPS/route/weather data so it can run without privileged railway APIs. The API boundary is intentionally isolated: replace the data generation in `main.py` with authorised live railway/GPS feeds and replace the transparent demo predictor with the trained TensorFlow ANN + GA pipeline described in the presentation.

The presentation specifies Railway/GPS APIs, Mapbox, WebSocket, FastAPI, ANN, TensorFlow, PostgreSQL, Redis, NumPy/Pandas and Genetic Algorithm as the intended stack, and describes continuous ETA updates, early delay detection, confidence scores and API integration. The demo implements the core user-facing flow while keeping external/production credentials out of the project.
