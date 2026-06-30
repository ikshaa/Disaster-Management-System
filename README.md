
# AI Disaster Response Coordinator

An AI system that receives disaster reports from citizens, automatically ranks them by urgency using NLP and computer vision, and shows emergency responders a live prioritized dashboard — even when there is **no internet** (Phase 2 mesh network).

Built for **Imagine RIT**. Designed for real-world deployment.

---

## How It Works

```
PHASE 1 — Internet path (direct submission)

  Citizen (web form)
       │  text + photo + GPS
       ▼
  FastAPI Backend  ──►  DistilBERT (NLP)  ──► text score
                   ──►  ResNet50 (Vision) ──► image score
                   ──►  GPS clustering    ──► location risk
                   │
                   │  FinalPriority = (text × 0.6) + (image × 0.3) + (location × 0.1)
                   │
                   ▼  WebSocket broadcast
  React Dashboard  ──►  Live map + ranked alert list + dispatch


PHASE 2 — Offline mesh path (no internet needed)

  Citizen (phone on local WiFi)
       │  connects to relay node, no internet required
       ▼
  Mesh Relay Node  ──►  stores locally in SQLite queue
       │  (relay node moves / gains connectivity)
       ▼  POST /sync
  FastAPI Backend  ──►  same AI pipeline as above
       ▼
  Dashboard updates live — reports appear as they sync
```

---

## Emergency Classification

| Class | Base Score | Level | Example keywords |
|-------|-----------|-------|-----------------|
| People trapped | 10 | CRITICAL | trapped, buried, stuck, cannot move |
| Injured people | 9 | CRITICAL | bleeding, unconscious, dying, severe |
| Infrastructure collapse | 8 | HIGH | collapsed, structural, building down |
| Fire damage | 8 | HIGH | fire, burning, flames, smoke |
| Request for rescue | 7 | HIGH | rescue, help, SOS, emergency |
| Flood damage | 6 | MEDIUM | flood, flooding, water rising |
| Low priority | 2 | LOW | minor, debris, small damage |

Final score = base × confidence × 0.6 + image score × 0.3 + location risk × 0.1

---

## Prerequisites

- Python 3.11+ with `venv`
- Node.js 18+
- Git with SSH configured to GitHub

**First-time setup — install dependencies:**

```bash
# Python dependencies (backend + AI)
source venv/bin/activate
pip install -r backend/requirements.txt

# Frontend dependencies
cd frontend && npm install && cd ..
```

**Train the AI models** (weights are not in the repo — too large for GitHub):

```bash
source venv/bin/activate

# 1. Train DistilBERT NLP classifier (~20 min on CPU, 22k crisis tweets)
cd model/backend/ai
python bert_classifier.py train --epochs 3
cd ../../..

# 2. Train ResNet50 image classifier (~requires AIDER dataset in ai-models/data/)
cd ai-models/src
python train.py
cd ../..
```

> The system falls back to a keyword-based NLP classifier automatically if the DistilBERT weights are missing — all other features still work.

---

## Running the System

### Option 1 — One command (recommended)

```bash
bash start.sh
```

Opens:
- **Responder dashboard:** http://localhost:3000
- **API + docs:** http://localhost:8000/docs

### Option 2 — Manual (separate terminals)

**Terminal 1 — Backend (AI hub):**
```bash
cd backend
source ../venv/bin/activate
uvicorn main:app --port 8000 --reload
```

**Terminal 2 — Frontend (dashboard):**
```bash
cd frontend
npm run dev
```

**Terminal 3 — Mesh relay node (Phase 2, optional):**
```bash
source venv/bin/activate
python -m uvicorn mesh.relay:app --port 8001 --reload
```

### Option 3 — Docker

```bash
docker-compose up --build
```

---

## Submitting a Report — Citizens

### Direct (Phase 1 — needs internet)

1. Open **http://localhost:3000**
2. Click **"+ Submit Report"** in the top-right panel
3. Fill in:
   - **Situation** — describe what's happening in plain text
   - **Location** — click "Use my location" or enter lat/lng manually
   - **Photo** — optional, but boosts AI score (ResNet50 analyzes it)
4. Click **Submit Report**
5. AI scores it in under 2 seconds → appears instantly on the map and ranked list

### Via mesh relay (Phase 2 — no internet needed)

1. Citizen connects to the relay node's local WiFi hotspot
2. Opens **http://[relay-ip]:8001** in any phone browser
3. Fills in the form and submits
4. Report is stored locally on the relay — no internet required
5. When the relay reaches the hub: `POST http://localhost:8001/sync`
6. All queued reports flow through the AI pipeline → appear live on dashboard

### Offline PWA (Phase 2 — phone goes offline)

1. Open **http://localhost:3000/citizen**
2. The form detects offline status and shows an orange "OFFLINE" badge
3. Submit normally → saved to the phone's localStorage queue
4. When the phone reconnects, reports auto-sync to the hub

---

## Using the Dashboard — Responders

| Element | Description |
|---------|-------------|
| **Header stats** | Live counts: Total / Pending / Critical / Dispatched. Green dot = WebSocket live. |
| **Map (left panel)** | Leaflet map with colored markers. Red = CRITICAL, Orange = HIGH, Yellow = MEDIUM, Green = LOW. Larger circle = higher priority. Click any marker for details. |
| **Priority list (right panel)** | All reports sorted by AI score, highest first. Shows NLP category, image class, and priority badge. Click to open full detail. |
| **Report detail modal** | Full AI reasoning breakdown: NLP class + confidence, image damage class, location cluster, score formula. Dispatch button assigns a responder team. |
| **Submit Report button** | Opens the citizen form — useful for staff submitting reports on behalf of callers. |

---

## Running the Demo (Imagine RIT)

### Phase 1 demo — fire 20 AI-ranked reports

```bash
source venv/bin/activate
python simulator/generate_reports.py
```

Then submit a live report on stage:
> *"3 people trapped, building collapsed on Main St"*

Watch it jump to #1 in real time.

### Phase 2 demo — full mesh relay flow

```bash
# Start the relay node first (Terminal 3)
python -m uvicorn mesh.relay:app --port 8001

# Then run the automated demo script
source venv/bin/activate
python mesh/demo_mesh.py --reset
```

The script walks through 7 steps on screen:
1. Checks relay is running
2. Submits 5 reports to relay (no internet — hub sees nothing)
3. Shows queue status: "5 pending, 0 synced"
4. Checks hub: reports not there yet
5. Triggers sync: relay forwards all to hub through AI pipeline
6. Queue status: "0 pending, 5 synced"
7. Shows hub priority list — reports now ranked and on dashboard

**Demo talking points:**
- Step 2: *"Citizens are submitting via local WiFi — no internet. The AI hub sees nothing yet."*
- Step 5: *"The relay truck drives to the responder hub. It gains connectivity."*
- Step 6: *"All 5 reports sync through the same AI pipeline. Dashboard updates live."*
- End: *"Zero changes to the AI engine. Only the ingestion layer changed."*

---

## Project Structure

```
Disaster-Management-System/
│
├── backend/                        # Phase 1 — FastAPI AI hub
│   ├── main.py                     # App entry point + WebSocket manager
│   ├── requirements.txt
│   ├── ai/
│   │   ├── nlp_assessor.py         # DistilBERT + keyword fallback (hybrid)
│   │   ├── vision_assessor.py      # ResNet50 image damage classifier
│   │   └── priority_engine.py      # Score formula + location risk
│   ├── api/
│   │   ├── routes.py               # All REST endpoints + /mesh/sync
│   │   └── models.py               # Pydantic schemas
│   ├── db/
│   │   ├── database.py             # SQLAlchemy + SQLite setup
│   │   ├── schemas.py              # ORM table definitions
│   │   └── crud.py                 # DB operations + hotspot clustering
│   └── ws_manager.py               # WebSocket connection manager
│
├── frontend/                       # React dashboard + citizen PWA
│   ├── public/
│   │   ├── manifest.json           # PWA manifest (installable on phone)
│   │   └── sw.js                   # Service worker (offline app shell cache)
│   └── src/
│       ├── App.jsx                 # Routes: / → dashboard, /citizen → form
│       ├── components/
│       │   ├── Dashboard.jsx       # Main layout (map + list)
│       │   ├── ReportMap.jsx       # Leaflet map with colored markers
│       │   ├── PriorityList.jsx    # AI-ranked alert list
│       │   ├── ReportForm.jsx      # Staff/citizen form (in dashboard)
│       │   ├── ReportDetail.jsx    # AI reasoning modal + dispatch
│       │   └── CitizenForm.jsx     # Offline-capable citizen PWA (/citizen)
│       └── services/
│           ├── api.js              # Axios API calls
│           └── websocket.js        # WebSocket auto-reconnect client
│
├── mesh/                           # Phase 2 — Mesh relay node
│   ├── relay.py                    # Standalone edge server (no AI imports)
│   └── demo_mesh.py                # End-to-end Phase 2 demo script
│
├── ai-models/                      # ResNet50 image classifier
│   ├── src/
│   │   ├── train.py                # Training pipeline
│   │   ├── evaluate.py             # Evaluation + metrics
│   │   ├── dataset.py              # AIDER dataset loader
│   │   ├── augmentation.py         # Albumentations transforms
│   │   └── preprocess.py           # Image preprocessing
│   └── outputs/
│       └── best_model.pt           # Trained weights (not in repo — train locally)
│
├── model/                          # DistilBERT NLP classifier
│   ├── backend/ai/
│   │   ├── bert_classifier.py      # DistilBERT train + inference
│   │   ├── nlp_classifier.py       # NLTK keyword fallback
│   │   ├── text_scoring.py         # Priority score computation
│   │   └── preprocess_dataset.py   # CrisisNLP data preprocessing
│   └── models/
│       └── distilbert_crisis_classifier/  # Saved model (weights not in repo)
│
├── simulator/
│   └── generate_reports.py         # Fires 20 fake disaster reports for demo
│
├── docker-compose.yml
├── start.sh                        # One-command startup (backend + frontend)
├── CLAUDE.md                       # Project context for Claude AI sessions
└── README.md                       # This file
```

---

## API Reference

### Phase 1 — Direct Reports

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| `POST` | `/api/v1/reports` | `multipart/form-data`: `text_message`, `latitude`, `longitude`, `image` (optional) | Submit report → runs AI → broadcasts via WebSocket |
| `GET` | `/api/v1/reports` | `?status=pending&limit=50` | List reports (filtered, paginated) |
| `GET` | `/api/v1/reports/{id}` | — | Full report with AI reasoning JSON |
| `GET` | `/api/v1/prioritized` | — | All reports sorted by `final_priority` descending |
| `POST` | `/api/v1/reports/{id}/dispatch` | `{"responder_id": "...", "notes": "..."}` | Mark dispatched, log to `dispatch_log`, emit WebSocket event |
| `GET` | `/api/v1/hotspots` | — | GPS clusters (center lat/lng, report count, avg priority) |
| `GET` | `/api/v1/stats` | — | `{total, pending, dispatched, resolved, critical}` |
| `WS` | `/ws/live` | — | WebSocket — pushes `new_report` and `report_updated` events |

### Phase 2 — Mesh

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/mesh/sync` | Batch JSON reports from relay → runs AI on each → broadcasts |

### Relay Node (port 8001)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Citizen HTML form (works on any phone, no internet) |
| `POST` | `/submit` | Citizen submits report → stored in local SQLite queue |
| `POST` | `/sync?hub_url=...` | Forward all pending reports to hub |
| `GET` | `/status` | `{pending, synced, total}` |
| `GET` | `/queue` | List all queued reports |
| `POST` | `/reset` | Clear the queue (for demo resets) |

---

## AI Models

### NLP Classifier (DistilBERT)
- Fine-tuned on 22,099 CrisisNLP crisis tweets
- 7 emergency classes with confidence scores
- Hybrid mode: DistilBERT primary, keyword fallback if model unavailable or downgrades to low-priority when keywords say otherwise
- Retrain: `python model/backend/ai/bert_classifier.py train --epochs 3`

### Vision Classifier (ResNet50)
- Fine-tuned on AIDER dataset (disaster images)
- 5 classes: `fire`, `flooded_areas`, `collapsed_building`, `traffic_incident`, `normal`
- 97.4% test accuracy
- Weights: `ai-models/outputs/best_model.pt` (not in repo — 210MB)
- Retrain: `python ai-models/src/train.py`

### Priority Score Formula
```
FinalPriority = (TextScore × 0.6) + (ImageScore × 0.3) + (LocationRisk × 0.1)

TextScore    = base_score × nlp_confidence          (0–10)
ImageScore   = base_score × vision_confidence       (0–10, 0 if no image)
LocationRisk = f(nearby reports within 500m radius) (0–10)
```

---

## Team

| Member | Area |
|--------|------|
| ikshaa (Neha) | AI image models — ResNet50 pipeline (`ai-models/`) |
| gsam99 | NLP/text AI — DistilBERT classifier (`model/`) |

GitHub repo: https://github.com/gsam99/Disaster-Management-System (branch: `feature/ai-models`)
