# AI Disaster Response Coordinator — Project Context for Claude

## What This Is
An AI-powered disaster response system built for **Imagine RIT** (university showcase/competition) and real-world deployment. Citizens submit disaster reports (text + image + GPS). AI ranks them by urgency and displays them on a live emergency dashboard for responders.

**Build time:** 3 weeks. **Current phase:** Phase 1 (AI Demo).

## Team & Ownership
- **ikshaa (Neha)** — AI/image models (`ai-models/`) — ResNet50 image classifier done
- **gsam99** — NLP/text AI (`model/`) — DistilBERT classifier done
- **[3rd teammate]** — TBD

## Architecture (5 Layers)
```
Layer 1 — INPUT:        Citizen web form / Android app / Report simulator
Layer 2 — BACKEND:      Python FastAPI + Uvicorn + CORS
Layer 3 — INTELLIGENCE: NLP Classifier + Vision Model + Score Aggregator
Layer 4 — STORAGE:      SQLite (dev) → PostgreSQL (prod) + Redis cache
Layer 5 — OUTPUT:       React 18 dashboard + Leaflet.js map + WebSocket live feed
```

## Tech Stack
| Area | Technologies |
|------|-------------|
| Frontend | React 18, Leaflet.js, TailwindCSS, Axios, socket.io-client, Recharts |
| Backend | Python 3.11, FastAPI, Uvicorn, SQLAlchemy, Alembic, python-multipart |
| AI/ML | DistilBERT, HuggingFace Transformers, YOLOv8, PyTorch, scikit-learn |
| Database | SQLite (Phase 1), PostgreSQL (Phase 2), Redis |
| DevOps | Docker, Docker Compose, GitHub Actions CI, pytest |

## AI Priority Score Formula
```
FinalPriority = (TextScore × 0.6) + (ImageScore × 0.3) + (LocationRisk × 0.1)
```
- LocationRisk increases when multiple reports cluster within 500m radius
- Score range: 0.0 – 10.0

## Emergency Classification
| Class | Score | Level | Keywords |
|-------|-------|-------|----------|
| Trapped Person | 10/10 | CRITICAL | trapped, buried, stuck, cannot move |
| Severe Injury | 9/10 | CRITICAL | bleeding, unconscious, dying, severe |
| Infrastructure Collapse | 8/10 | HIGH | collapsed, structural, building down |
| Flooding / Fire | 6/10 | MEDIUM | flood, fire, smoke, burning, water |
| Minor Issue | 3/10 | LOW | road, debris, minor, small damage |

## API Endpoints (to build)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /api/v1/reports | Submit report (text + image + GPS) |
| GET | /api/v1/reports | List all reports (paginated) |
| GET | /api/v1/reports/{id} | Full report + AI reasoning |
| GET | /api/v1/prioritized | All reports sorted by priority |
| POST | /api/v1/reports/{id}/dispatch | Mark dispatched, emit WebSocket event |
| GET | /api/v1/hotspots | Clustered GPS coords for heatmap |
| WS | /ws/live | Real-time push to all dashboards |

## Target File Structure (what needs to be built)
```
disaster-response/
  backend/
    main.py                        # FastAPI entry point
    api/routes.py                  # All endpoints
    api/models.py                  # Pydantic schemas
    ai/nlp_classifier.py           # DistilBERT text scoring
    ai/vision_assessor.py          # YOLOv8 image analysis
    ai/priority_engine.py          # Score aggregator
    ai/keyword_fallback.py         # Rule-based fallback (no GPU)
    db/database.py                 # SQLAlchemy setup
    db/crud.py                     # DB operations
    db/schemas.py                  # Table definitions
    requirements.txt
    .env
  frontend/src/
    components/Dashboard.jsx
    components/ReportMap.jsx       # Leaflet + heatmap
    components/PriorityList.jsx    # Ranked alert list
    components/ReportDetail.jsx    # AI reasoning modal
    components/ReportForm.jsx      # Citizen submission
    services/api.js                # Axios calls
    services/websocket.js          # Live updates
  simulator/generate_reports.py   # Batch fake reports for demo
  docker-compose.yml
```

## What's Already Done
- [x] ResNet50 image classifier (97.4% test accuracy) — `ai-models/src/`
- [x] Data augmentation, EDA, preprocessing pipeline — `ai-models/src/`
- [x] Trained model weights — `ai-models/outputs/best_model.pt`
- [x] DistilBERT crisis tweet NLP classifier — `model/backend/ai/`
- [x] CrisisNLP labeled dataset — `model/CrisisNLP_labeled_data_crowdflower/`
- [x] Preprocessed text data — `model/data/clean.csv`

## What's Needed Next (Week 1 — Backend MVP)
- [ ] FastAPI project setup with Docker Compose
- [ ] POST /reports and GET /prioritized endpoints
- [ ] Keyword-based text scoring fallback (no GPU needed)
- [ ] Wire in existing DistilBERT model from `model/backend/ai/`
- [ ] SQLite + SQLAlchemy setup with Alembic migrations
- [ ] Test with 10 sample reports to verify priority ordering

## Week 2 (Vision AI + Hotspots)
- [ ] Wire in existing ResNet50 model from `ai-models/` as vision_assessor
- [ ] Add YOLOv8 or use existing ResNet for damage classification
- [ ] Image upload handling (multipart)
- [ ] Priority score aggregator
- [ ] GPS clustering for hotspot detection
- [ ] AI reasoning JSON output

## Week 3 (Dashboard + Demo)
- [ ] React dashboard with priority-sorted list
- [ ] Leaflet.js map with heatmap
- [ ] WebSocket real-time feed
- [ ] Report detail modal with AI reasoning
- [ ] Report simulator script (20 fake alerts for demo)
- [ ] Docker Compose deploy + demo rehearsal

## Phase 2 (After Imagine RIT)
Replace only the input layer with Bluetooth/Wi-Fi Direct mesh network. Store-and-forward caching on mesh nodes. Zero changes to AI engine, scoring, or dashboard.

## Demo Script (Imagine RIT)
1. Open empty dashboard: "Right now there's no disaster. Let's simulate one."
2. Run simulator → 20 reports appear live via WebSocket
3. Show auto-ranking: "AI ranked 20 messages in under one second"
4. Show map heatmap cluster: "AI amplifying urgency automatically"
5. Click top report → show AI reasoning panel (keywords, confidence, score)
6. Submit live: type "3 people trapped, building collapsed" → watch it jump to #1
7. Mention Phase 2: "This runs offline over mesh in a real disaster zone"

## Database Schema (key tables)
- **reports**: id, timestamp, text_message, image_path, lat, lng, text_score, image_score, location_risk, final_priority, ai_reasoning (JSON), status
- **hotspot_clusters**: id, center_lat, center_lng, report_count, avg_priority, updated_at
- **dispatch_log**: id, report_id (FK), dispatched_at, responder_id, notes
