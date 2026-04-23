# AI Disaster Response Coordinator — Project Context for Claude

## What This Is
An AI-powered disaster response system built for **Imagine RIT** and real-world deployment. Citizens submit disaster reports (text + image + GPS). AI ranks them by urgency. Responders see a live emergency dashboard. Works offline via a mesh relay network (Phase 2).

**Both Phase 1 and Phase 2 are complete and working.**

---

## Team
- **ikshaa (Neha)** — AI image models (`ai-models/`), full-stack integration, Phase 2 mesh
- **gsam99** — NLP/text AI (`model/`), DistilBERT classifier
- **[3rd teammate]** — TBD

GitHub: `https://github.com/gsam99/Disaster-Management-System` · branch: `feature/ai-models`

---

## Architecture

```
PHASE 1 (internet)
  Citizen web form → FastAPI backend → AI pipeline → WebSocket → React dashboard

PHASE 2 (no internet)
  Citizen phone → Mesh Relay Node (local WiFi) → stores locally
                  → sync when connected → same AI pipeline → dashboard
```

**5-layer design:**
```
Layer 1 — INPUT:        Web form / Citizen PWA / Relay node / Simulator
Layer 2 — BACKEND:      Python FastAPI + Uvicorn + CORS + WebSocket
Layer 3 — INTELLIGENCE: DistilBERT NLP + ResNet50 Vision + Priority Engine
Layer 4 — STORAGE:      SQLite (dev) → PostgreSQL (prod)
Layer 5 — OUTPUT:       React 18 dashboard + Leaflet.js map + live feed
```

---

## Tech Stack

| Area | Technologies |
|------|-------------|
| Frontend | React 18, Leaflet.js, TailwindCSS, Axios, native WebSocket |
| Backend | Python 3.11+, FastAPI, Uvicorn, SQLAlchemy, python-multipart |
| AI/ML | DistilBERT (HuggingFace Transformers), ResNet50 (PyTorch/torchvision), NLTK fallback |
| Database | SQLite (dev) — file: `backend/disaster_reports.db` |
| Mesh | FastAPI relay node, SQLite queue, httpx for sync |
| DevOps | Docker, Docker Compose, `start.sh` |

---

## AI Priority Score Formula
```
FinalPriority = (TextScore × 0.6) + (ImageScore × 0.3) + (LocationRisk × 0.1)

TextScore    = base_score × nlp_confidence   (0–10)
ImageScore   = base_score × vision_conf      (0–10, 0 if no image)
LocationRisk = f(reports within 500m radius) (0, 2, 5, 8, or 10)
```

---

## Emergency Classes

| Class | Base Score | Level |
|-------|-----------|-------|
| People trapped | 10 | CRITICAL |
| Injured people | 9 | CRITICAL |
| Infrastructure collapse | 8 | HIGH |
| Fire damage | 8 | HIGH |
| Request for rescue | 7 | HIGH |
| Flood damage | 6 | MEDIUM |
| Low priority | 2 | LOW |

---

## How to Run

```bash
# Full system (Phase 1)
bash start.sh
# → Backend: http://localhost:8000
# → Dashboard: http://localhost:3000
# → API docs: http://localhost:8000/docs
# → Citizen PWA: http://localhost:3000/citizen

# Phase 2 mesh relay node (separate terminal)
source venv/bin/activate
python -m uvicorn mesh.relay:app --port 8001 --reload
# → Citizen relay form: http://localhost:8001

# Demo simulator (fires 20 reports)
source venv/bin/activate
python simulator/generate_reports.py

# Phase 2 demo (full mesh flow)
python mesh/demo_mesh.py --reset
```

---

## Complete File Map

### Backend (`backend/`)
| File | Purpose |
|------|---------|
| `main.py` | FastAPI app entry, WebSocket endpoint `/ws/live`, mounts `/uploads` |
| `ws_manager.py` | ConnectionManager — broadcasts to all connected dashboards |
| `requirements.txt` | fastapi, uvicorn, sqlalchemy, python-multipart, pillow, torch, transformers |
| `ai/nlp_assessor.py` | Loads DistilBERT from `model/models/distilbert_crisis_classifier/`, falls back to keyword classifier. Hybrid: if DistilBERT downgrades to low-priority but keywords say otherwise, keyword wins. |
| `ai/vision_assessor.py` | Loads ResNet50 from `ai-models/outputs/best_model.pt`. 5 classes: fire, flooded_areas, collapsed_building, traffic_incident, normal. Returns image_score 0–9. |
| `ai/priority_engine.py` | `compute_location_risk()`, `compute_final_priority()`, `build_ai_reasoning()` |
| `api/routes.py` | All endpoints + Phase 2 `POST /api/v1/mesh/sync` batch endpoint |
| `api/models.py` | Pydantic: `ReportResponse`, `DispatchRequest`, `StatsResponse`, `HotspotResponse` |
| `db/schemas.py` | SQLAlchemy ORM: `Report`, `DispatchLog` tables |
| `db/database.py` | SQLite engine, `init_db()`, `get_db()` dependency |
| `db/crud.py` | `create_report`, `get_report`, `get_prioritized`, `dispatch_report`, `get_hotspots`, `count_nearby_reports` (Haversine), `get_stats` |

### Frontend (`frontend/src/`)
| File | Purpose |
|------|---------|
| `App.jsx` | Routes: `/citizen` → CitizenForm, everything else → Dashboard. Registers SW in prod. |
| `components/Dashboard.jsx` | Layout: map left, list right, modals overlay |
| `components/ReportMap.jsx` | Leaflet map — colored CircleMarkers sized by priority, click → detail |
| `components/PriorityList.jsx` | Scrollable list sorted by priority, color-coded severity badges |
| `components/ReportForm.jsx` | Staff/citizen form in dashboard (text + lat/lng + image upload) |
| `components/ReportDetail.jsx` | AI reasoning modal: NLP class, image class, score breakdown, Dispatch button |
| `components/CitizenForm.jsx` | Phase 2 offline-capable PWA form at `/citizen`. Detects online/offline, queues to localStorage, auto-syncs. Configurable relay URL via ⚙ button. |
| `services/api.js` | Axios calls: getPrioritized, getReport, getStats, getHotspots, submitReport, dispatchReport |
| `services/websocket.js` | Auto-reconnecting WebSocket client, calls `onMessage(data)` for `new_report` / `report_updated` events |
| `public/manifest.json` | PWA manifest — makes citizen form installable on phones |
| `public/sw.js` | Service worker — caches app shell for offline viewing |

### Mesh (`mesh/`)
| File | Purpose |
|------|---------|
| `relay.py` | Standalone FastAPI server. Serves citizen HTML form at `/`. Endpoints: `/submit` (queue report), `/sync` (forward to hub), `/status`, `/queue`, `/reset`. Zero imports from `backend/`. Uses httpx to POST to hub's `/api/v1/reports` one-by-one on sync. |
| `demo_mesh.py` | 7-step demo script: checks relay → submits 5 reports to relay → verifies hub doesn't see them → triggers sync → verifies hub now has them → shows prioritized list |

### AI Models (existing, not changed)
| File | Purpose |
|------|---------|
| `model/backend/ai/bert_classifier.py` | DistilBERT train + `classify(text)` + `analyze(text)` |
| `model/backend/ai/nlp_classifier.py` | NLTK keyword classifier (fallback) |
| `model/backend/ai/text_scoring.py` | `compute_text_score(category, confidence)` |
| `ai-models/src/train.py` | ResNet50 training, `build_model()` — architecture must match `evaluate.py` |
| `ai-models/src/evaluate.py` | `load_model(checkpoint_path, device)` — used by vision_assessor |

---

## Key Integration Points

**NLP classifier path:** `backend/ai/nlp_assessor.py` → loads from `model/models/distilbert_crisis_classifier/` → fallback to keyword matching in same file.

**Vision classifier path:** `backend/ai/vision_assessor.py` → loads checkpoint from `ai-models/outputs/best_model.pt` → must rebuild same ResNet50 architecture as in `ai-models/src/train.py`.

**Mesh sync path:** `mesh/relay.py POST /sync` → calls `backend POST /api/v1/reports` per report (multipart) → same AI pipeline as direct submission.

**WebSocket path:** Any new report → `crud.create_report()` → `manager.broadcast({"type": "new_report", ...})` → all connected dashboards update in real time.

---

## Model Weights (not in repo — too large)

| Model | Path | Size | How to get |
|-------|------|------|-----------|
| ResNet50 | `ai-models/outputs/best_model.pt` | 210MB | Run `python ai-models/src/train.py` |
| DistilBERT | `model/models/distilbert_crisis_classifier/model.safetensors` | 267MB | Run `python model/backend/ai/bert_classifier.py train` |

Both models have graceful fallbacks — the system runs without them (lower accuracy).

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/reports` | Submit report (multipart: text + image + GPS) |
| GET | `/api/v1/reports` | List reports (`?status=pending&limit=50`) |
| GET | `/api/v1/reports/{id}` | Full report + AI reasoning |
| GET | `/api/v1/prioritized` | All reports sorted by priority |
| POST | `/api/v1/reports/{id}/dispatch` | Mark dispatched + emit WebSocket |
| GET | `/api/v1/hotspots` | GPS clusters for heatmap |
| GET | `/api/v1/stats` | `{total, pending, dispatched, resolved, critical}` |
| WS | `/ws/live` | Real-time feed |
| POST | `/api/v1/mesh/sync` | Batch JSON reports from relay node |

**Relay node (port 8001):**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Citizen HTML form |
| POST | `/submit` | Queue report locally |
| POST | `/sync?hub_url=...` | Sync all pending to hub |
| GET | `/status` | Queue counts |
| POST | `/reset` | Clear queue (demo resets) |

---

## Demo Script (Imagine RIT)

### Phase 1
1. Open dashboard at http://localhost:3000 — empty state
2. Run: `python simulator/generate_reports.py` — 20 reports appear live
3. *"AI ranked 20 messages in under a second. No human involved."*
4. Show map heatmap — red clusters = high-risk zones
5. Click top report → AI reasoning panel (NLP class, confidence, score formula)
6. Submit live: *"3 people trapped, building collapsed"* → watch it hit #1 instantly
7. *"Now let me show you what happens when the internet goes down."*

### Phase 2
8. Open http://localhost:8001 — lightweight relay form
9. *"Citizens connect to this over local WiFi. No internet."*
10. Submit 3 reports via relay — nothing on dashboard
11. `python mesh/demo_mesh.py --reset` — run sync
12. Watch 5 reports appear on dashboard live
13. *"Same AI. Same scoring. Same dashboard. Only the ingestion layer changed."*

---

## Database Schema

**`reports` table:**
`id`, `timestamp`, `text_message`, `image_path`, `latitude`, `longitude`, `text_score`, `image_score`, `location_risk`, `final_priority`, `nlp_category`, `nlp_confidence`, `image_class`, `image_confidence`, `ai_reasoning` (JSON string), `status` (pending/dispatched/resolved)

**`dispatch_log` table:**
`id`, `report_id`, `dispatched_at`, `responder_id`, `notes`

**`relay_queue.db` (relay-local, separate DB):**
`id`, `received_at`, `text_message`, `latitude`, `longitude`, `image_data` (BLOB), `image_filename`, `synced`, `synced_at`
