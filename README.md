# AI Disaster Response Coordinator

An AI system that lets citizens report disasters (text + photo + GPS), automatically ranks them by urgency using NLP and computer vision, and shows responders a live emergency dashboard.

Built for **Imagine RIT**. Stack: Python · FastAPI · React · DistilBERT · ResNet50.

---

## What It Does

```
Citizen submits report
        ↓
   AI analyzes it
   ├── NLP (DistilBERT) → classifies text → text score
   ├── Vision (ResNet50) → analyzes photo → image score
   └── GPS clustering → nearby reports → location risk
        ↓
   Priority Score = (text × 0.6) + (image × 0.3) + (location × 0.1)
        ↓
   Dashboard updates live (WebSocket)
   Responder sees ranked list + map → dispatches help
```

**Emergency classes:**

| Class | Score | Level |
|-------|-------|-------|
| People trapped | 10 | CRITICAL |
| Injured people | 9 | CRITICAL |
| Infrastructure collapse | 8 | HIGH |
| Fire damage | 8 | HIGH |
| Request for rescue | 7 | HIGH |
| Flood damage | 6 | MEDIUM |
| Low priority | 2 | LOW |

---

## How to Run

### Option 1 — One command (recommended)

```bash
bash start.sh
```

Then open:
- **Dashboard (responders):** http://localhost:3000
- **Report form (citizens):** http://localhost:3000 → click **"+ Submit Report"**
- **API docs:** http://localhost:8000/docs

### Option 2 — Manual (two terminals)

**Terminal 1 — Backend:**
```bash
cd backend
source ../venv/bin/activate
uvicorn main:app --port 8000 --reload
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

### Option 3 — Docker

```bash
docker-compose up --build
```

---

## How to Submit a Report (Citizens)

1. Open http://localhost:3000
2. Click **"+ Submit Report"** (top-right of the panel)
3. Fill in:
   - **Situation** — describe what's happening (e.g. "Building collapsed, 3 people trapped")
   - **Location** — click **"Use my location"** or type lat/lng manually
   - **Photo** — optional but improves the AI score (upload a photo of the disaster area)
4. Click **Submit Report**
5. The AI scores it in under 2 seconds and it appears live on the map and ranked list

---

## How to Use the Dashboard (Responders)

| Element | What it does |
|---------|-------------|
| Map (left) | Shows all reports as colored markers — red = critical, orange = high, yellow = medium, green = low. Bigger circle = higher priority. Click a marker to see details. |
| Priority list (right) | All reports sorted by AI score, highest first. Click any report to see full AI reasoning. |
| Report detail modal | Shows the report text, photo, AI breakdown (NLP class, image class, score formula), and a **Dispatch** button to assign a responder. |
| Header stats | Live counts: total reports, pending, critical, dispatched. Green dot = WebSocket live. |

---

## Demo (Imagine RIT)

Fire 20 fake reports to fill the dashboard:

```bash
source venv/bin/activate
python simulator/generate_reports.py
```

Then submit a live report on stage:
> *"3 people trapped, building collapsed on Main St"*

Watch it jump to #1 instantly.

---

## Project Structure

```
Disaster-Management-System/
├── backend/                  # FastAPI server
│   ├── main.py               # App entry + WebSocket
│   ├── ai/
│   │   ├── nlp_assessor.py   # DistilBERT + keyword fallback
│   │   ├── vision_assessor.py# ResNet50 image classifier
│   │   └── priority_engine.py# Score formula + location risk
│   ├── api/routes.py         # All API endpoints
│   ├── db/                   # SQLite + SQLAlchemy
│   └── uploads/              # Saved report images
├── frontend/                 # React dashboard
│   └── src/components/
│       ├── Dashboard.jsx     # Main layout
│       ├── ReportMap.jsx     # Leaflet map
│       ├── PriorityList.jsx  # Sorted alert list
│       ├── ReportForm.jsx    # Citizen submission form
│       └── ReportDetail.jsx  # AI reasoning modal + dispatch
├── ai-models/                # ResNet50 image model (trained, 97.4% acc)
│   └── outputs/best_model.pt
├── model/                    # DistilBERT NLP model (trained on CrisisNLP)
│   └── models/distilbert_crisis_classifier/
├── simulator/
│   └── generate_reports.py   # Demo report generator
├── docker-compose.yml
└── start.sh                  # One-command startup
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/reports` | Submit report (text + image + GPS) |
| GET | `/api/v1/prioritized` | All reports sorted by priority |
| GET | `/api/v1/reports/{id}` | Full report + AI reasoning |
| POST | `/api/v1/reports/{id}/dispatch` | Mark dispatched |
| GET | `/api/v1/hotspots` | GPS clusters for heatmap |
| GET | `/api/v1/stats` | Counts by status |
| WS | `/ws/live` | Real-time WebSocket feed |
