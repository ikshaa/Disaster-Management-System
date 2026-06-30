# Rescue-AI: AI Disaster Response Coordinator
### Complete Project Documentation

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [NLP Pipeline — DistilBERT Text Classifier](#3-nlp-pipeline--distilbert-text-classifier)
4. [Image Classification — ResNet50 Vision Model](#4-image-classification--resnet50-vision-model)
5. [Priority Engine](#5-priority-engine)
6. [Backend — FastAPI](#6-backend--fastapi)
7. [Frontend — React Dashboard](#7-frontend--react-dashboard)
8. [Phase 2 — Offline Mesh Network](#8-phase-2--offline-mesh-network)
9. [Database](#9-database)
10. [How to Run Locally](#10-how-to-run-locally)
11. [Deployment](#11-deployment)
12. [Exhibitor Guide — How to Explain the Project](#12-exhibitor-guide--how-to-explain-the-project)

---

## 1. Project Overview

**Rescue-AI** is an AI-powered disaster response coordination system built for real-world emergency management. Citizens submit disaster reports (text + photo + GPS) through a web form. The AI pipeline instantly ranks every report by urgency and streams them to a live dashboard where emergency responders can see what needs attention first — no human triage needed.

### The Problem It Solves
During a disaster, emergency services are overwhelmed with calls and messages from panicked citizens. A responder cannot manually read 500 messages and decide which is most critical. Rescue-AI does this automatically in milliseconds using two AI models working in parallel.

### Key Numbers
- **Two AI models**: DistilBERT (NLP) + ResNet50 (Computer Vision)
- **7 emergency classes**: from "People trapped" (priority 10) to "Low priority" (priority 2)
- **5 image damage classes**: fire, flooded areas, collapsed building, traffic incident, normal
- **Real-time**: WebSocket broadcasts every new report to all connected dashboards instantly
- **Offline capable**: Phase 2 mesh relay works with no internet

### Team
- **Neha (ikshaa)** — AI image models, full-stack integration, Phase 2 mesh
- **Samhita (gsam99)** — NLP/text AI, DistilBERT classifier

---

## 2. System Architecture

```
PHASE 1 — Internet path

  Citizen (web form at /citizen)
       │  text message + optional photo + GPS coordinates
       ▼
  FastAPI Backend (port 8000)
       │
       ├──► DistilBERT NLP ──► text_score (0–10)
       ├──► ResNet50 Vision ──► image_score (0–10)
       └──► GPS Clustering  ──► location_risk (0–10)
                │
                │  FinalPriority = (text × 0.6) + (image × 0.3) + (location × 0.1)
                │  [if no image: text × 0.8 + location × 0.2]
                ▼
  SQLite Database ──► WebSocket broadcast
                          │
                          ▼
  React Dashboard (port 3000) — live map + ranked alert list
```

```
PHASE 2 — Offline mesh path (no internet needed)

  Citizen phone (connects to local WiFi hotspot)
       │
       ▼
  Mesh Relay Node (port 8001) — runs on a laptop/Raspberry Pi
       │  stores reports locally in relay_queue.db
       │  when internet returns → POST /sync → sends to main hub
       ▼
  Same AI pipeline → same dashboard
```

### Five-Layer Design

| Layer | Components |
|-------|-----------|
| 1. Input | Web form, Citizen PWA, Mesh relay, Simulator |
| 2. Backend | Python FastAPI + Uvicorn + WebSocket |
| 3. Intelligence | DistilBERT NLP + ResNet50 Vision + Priority Engine |
| 4. Storage | SQLite (local dev) |
| 5. Output | React dashboard + Leaflet.js map + live feed |

---

## 3. NLP Pipeline — DistilBERT Text Classifier

### What It Does
Takes the citizen's text message and classifies it into one of 7 emergency categories with a confidence score.

### Training Data — CrisisNLP Dataset
- **Source**: CrisisNLP Crowdflower dataset — real crisis tweets from disasters worldwide (earthquakes, floods, hurricanes)
- **Size**: ~10,000+ labeled tweets
- **Original labels**: 15 raw categories (e.g., "missing_trapped_or_found_people", "infrastructure_and_utilities_damage")
- **Mapped to 7 classes**:

| Raw CrisisNLP Label | Mapped To |
|--------------------|-----------|
| missing_trapped_or_found_people | people trapped |
| affected_people / injured_or_dead_people / deaths_reports | injured people |
| infrastructure_and_utilities_damage | infrastructure collapse |
| displaced_people_and_evacuations | request for rescue |
| donation_needs / caution / prevention / not_related | low priority situation |

### Text Preprocessing Pipeline
Before training, every tweet goes through:
1. **URL removal** — strip `https://...` links
2. **@mention removal** — strip Twitter @handles
3. **Hashtag expansion** — `#earthquake` becomes `earthquake`
4. **Whitespace normalization** — collapse multiple spaces
5. **Tokenization** — split into words (NLTK punkt tokenizer)
6. **Stopword removal** — remove "the", "a", "is", etc.
7. **Stemming** — reduce words to root ("collapsed" → "collaps")

### Model Architecture — DistilBERT
- **Base model**: `distilbert-base-uncased` (Hugging Face)
- **What is DistilBERT?** A smaller, faster version of BERT. BERT is a transformer model trained on all of Wikipedia + BookCorpus to understand language. DistilBERT retains 97% of BERT's performance at 40% smaller size.
- **Fine-tuning**: Added a classification head (linear layer) on top, trained on the CrisisNLP dataset for 3 epochs
- **Input**: Text up to 128 tokens
- **Output**: Probability distribution across 7 classes

### Training Config
```
Base model:    distilbert-base-uncased
Max length:    128 tokens
Epochs:        3
Optimizer:     AdamW
Batch size:    16
Train/Val:     80/20 split
Output:        model/models/distilbert_crisis_classifier/
```

### Hybrid Scoring — DistilBERT + Keyword Fallback
The system runs **both** DistilBERT and a keyword matcher simultaneously:

```python
# Keyword signals (always runs first)
KEYWORD_MAP = {
    "people trapped":  ["trapped", "stuck", "buried", "cannot move"],
    "injured people":  ["injured", "hurt", "bleeding", "unconscious"],
    "fire damage":     ["fire", "burning", "flames", "smoke"],
    ...
}

# Hybrid rule: if DistilBERT says "low priority" but keywords strongly
# suggest otherwise, trust the keywords
if bert_says_low_priority AND keywords_say_high_priority:
    use_keywords()
else:
    use_distilbert()
```

This prevents the model from missing obvious emergencies.

### Text Score Formula
```
text_score = base_score × nlp_confidence

Base scores by class:
  people trapped        → 10
  injured people        → 9
  infrastructure collapse → 8
  fire damage           → 8
  request for rescue    → 7
  flood damage          → 6
  low priority          → 2
```

**Example**: "3 people trapped in collapsed building"
- DistilBERT → "people trapped", confidence 0.94
- text_score = 10 × 0.94 = **9.4**

---

## 4. Image Classification — ResNet50 Vision Model

### What It Does
Takes an uploaded photo and classifies the type of damage visible, returning an image severity score.

### Training Data — AIDER Dataset
- **Source**: AIDER (Aerial Image Dataset for Emergency Response) — disaster images collected from news, social media, and aerial photography
- **5 classes**: fire, flooded_areas, collapsed_building, traffic_incident, normal
- **Split**: 80% train / 20% validation

### Data Augmentation
To make the model more robust, training images were augmented:
- Random horizontal flip
- Random rotation (±15°)
- Color jitter (brightness, contrast, saturation)
- Random crop and resize to 224×224
- Normalization with ImageNet mean/std

### Model Architecture — ResNet50
- **Base model**: ResNet50 pretrained on ImageNet (1.2 million images, 1000 classes)
- **What is ResNet50?** A 50-layer deep convolutional neural network. "Residual" refers to skip connections that let gradients flow backward during training without vanishing.

**Transfer Learning Strategy:**
```
ResNet50 (ImageNet pretrained)
  │
  ├── Early layers (FROZEN — detect edges, textures, colors)
  ├── Layer1, Layer2, Layer3 (FROZEN — shapes, patterns)
  ├── Layer4 (TRAINABLE — high-level disaster-specific features)
  └── FC head (REPLACED):
        Original: Linear(2048 → 1000)
        Ours:     Dropout(0.3)
                  Linear(2048 → 256)
                  ReLU
                  Dropout(0.2)
                  Linear(256 → 5)
```

Freezing early layers prevents overfitting and speeds up training — those layers already know how to detect edges and textures from ImageNet.

### Training Config
```
Base model:      ResNet50 (ImageNet weights)
Input size:      224×224 RGB
Batch size:      32
Epochs:          20
Learning rate:   0.0001 (small for fine-tuning)
Optimizer:       Adam
Scheduler:       ReduceLROnPlateau (reduce LR when val loss plateaus)
Loss:            CrossEntropyLoss
Device:          Apple M1 Pro MPS / CUDA / CPU
Output:          ai-models/outputs/best_model.pt (210MB)
```

### Image Score Formula
```
image_score = base_score × confidence

Base scores by class:
  collapsed_building → 9.0 (CRITICAL)
  fire               → 8.0 (CRITICAL)
  flooded_areas      → 6.0 (HIGH)
  traffic_incident   → 4.0 (MEDIUM)
  normal             → 0.0 (LOW)
```

**Example**: Photo of burning building
- ResNet50 → "fire", confidence 0.87
- image_score = 8.0 × 0.87 = **6.96**

### Inference Pipeline
```python
# 1. Load and resize image
img = Image.open(path).convert("RGB").resize((224, 224))

# 2. Normalize with ImageNet stats
arr = (arr / 255.0 - IMAGENET_MEAN) / IMAGENET_STD

# 3. Forward pass through ResNet50
with torch.no_grad():
    logits = model(tensor)
    probs = softmax(logits)

# 4. Return top class + confidence + score
```

---

## 5. Priority Engine

### Final Priority Formula

**With image:**
```
FinalPriority = (text_score × 0.6) + (image_score × 0.3) + (location_risk × 0.1)
```

**Without image (text-only submission):**
```
FinalPriority = (text_score × 0.8) + (location_risk × 0.2)
```

The image weight is redistributed to text when no photo is uploaded — the system doesn't penalize text-only reports.

### Location Risk — GPS Clustering
The system counts how many other reports were submitted within 500 meters (using the Haversine formula):

```
Nearby reports    → Location Risk Score
0                 → 0
1                 → 2
2                 → 5
3–4               → 8
5+                → 10
```

**Why this matters**: Multiple reports from the same area confirm a real emergency. A single report could be a false alarm; five reports from the same block cannot be.

### Worked Example
Citizen submits: *"Building collapsed on Main St, 3 people trapped"* + photo of rubble

```
NLP:      "people trapped", confidence 0.94
           text_score = 10 × 0.94 = 9.4

Vision:   "collapsed_building", confidence 0.81
           image_score = 9.0 × 0.81 = 7.29

Location: 2 other reports within 500m
           location_risk = 5.0

Final:    (9.4 × 0.6) + (7.29 × 0.3) + (5.0 × 0.1)
        = 5.64 + 2.19 + 0.50
        = 8.33 / 10  → HIGH PRIORITY
```

---

## 6. Backend — FastAPI

### File Structure
```
backend/
├── main.py              — FastAPI app, CORS, WebSocket, lifespan
├── ws_manager.py        — WebSocket connection manager (broadcasts to all dashboards)
├── requirements.txt     — Python dependencies
├── ai/
│   ├── nlp_assessor.py  — DistilBERT loader + classify_text()
│   ├── vision_assessor.py — ResNet50 loader + analyze_image()
│   └── priority_engine.py — Score formula + location clustering
├── api/
│   ├── routes.py        — All HTTP endpoints
│   └── models.py        — Pydantic response schemas
└── db/
    ├── database.py      — SQLite engine, init_db()
    ├── schemas.py       — SQLAlchemy ORM models
    └── crud.py          — DB operations (create, read, dispatch, hotspots)
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/reports` | Submit report (multipart: text + image + GPS) |
| GET | `/api/v1/prioritized` | All reports sorted by priority |
| GET | `/api/v1/reports/{id}` | Single report + AI reasoning breakdown |
| POST | `/api/v1/reports/{id}/dispatch` | Mark as dispatched |
| GET | `/api/v1/hotspots` | GPS clusters for heatmap |
| GET | `/api/v1/stats` | Total, pending, critical, dispatched counts |
| WS | `/ws/live` | Real-time WebSocket feed |
| POST | `/api/v1/mesh/sync` | Batch sync from relay node |

### Request Flow (POST /api/v1/reports)
```
1. Save uploaded image to disk (uploads/)
2. nlp_assessor.classify_text(text_message) → NLP result
3. vision_assessor.analyze_image(image_path) → Vision result (if image)
4. compute_location_risk(lat, lng) → count nearby reports via Haversine
5. compute_final_priority(text_score, image_score, location_risk)
6. build_ai_reasoning(...) → JSON explaining the score
7. crud.create_report(...) → save to SQLite
8. manager.broadcast({"type": "new_report", "report": {...}}) → WebSocket push
9. Return ReportResponse JSON
```

### Model Loading — Lazy + Cached
Both models load on first request and stay in memory:
```python
_vision_model = None  # loaded once, reused forever

def _load_model():
    global _vision_model
    if _vision_model is None:
        # load from disk → stays in memory
        _vision_model = load_resnet50()
    return _vision_model
```

---

## 7. Frontend — React Dashboard

### Pages
- `/` — Responder dashboard (map + priority list + stats)
- `/citizen` — Citizen report form (PWA, offline capable)

### Key Components

| Component | Purpose |
|-----------|---------|
| `Dashboard.jsx` | Layout — map left, list right |
| `ReportMap.jsx` | Leaflet.js map — color-coded circles by priority |
| `PriorityList.jsx` | Scrollable ranked list, red/yellow/green badges |
| `ReportDetail.jsx` | AI reasoning modal — shows NLP class, image class, score breakdown |
| `CitizenForm.jsx` | Offline-capable PWA form with GPS detection |
| `ReportForm.jsx` | Staff submission form inside dashboard |

### Real-Time Updates — WebSocket
```javascript
// Auto-reconnecting WebSocket client
const ws = new WebSocket("ws://localhost:8000/ws/live")

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data)
  if (msg.type === "new_report") {
    // Insert at top, resort by priority, deduplicate
  }
}
```

### Citizen Form — Offline PWA
- Detects GPS automatically via `navigator.geolocation`
- If offline: saves report to `localStorage` queue
- When internet returns: auto-syncs queued reports
- Service worker caches the app shell for offline viewing
- Installable on phones (PWA manifest)

---

## 8. Phase 2 — Offline Mesh Network

### The Problem
During major disasters, internet infrastructure often goes down. Citizens can't submit reports, responders lose the dashboard.

### The Solution
A lightweight **mesh relay node** runs on a laptop or Raspberry Pi at the disaster site. Citizens connect to it over local WiFi — no internet required. The relay stores reports locally and syncs them to the main hub when connectivity returns.

```
mesh/
├── relay.py       — Standalone FastAPI server (port 8001)
└── demo_mesh.py   — 7-step demo script
```

### Relay Endpoints
| Endpoint | Description |
|----------|-------------|
| `GET /` | Serves the citizen HTML form |
| `POST /submit` | Receives and queues a report locally |
| `POST /sync` | Forwards all queued reports to the hub |
| `GET /status` | Shows queue counts |
| `POST /reset` | Clears the queue (demo use) |

### How to Run Phase 2
```bash
# Terminal 3: Start relay node
source venv/bin/activate
python -m uvicorn mesh.relay:app --port 8001 --reload

# Citizens go to http://<your-laptop-ip>:8001 on their phones
# When internet returns, sync:
python mesh/demo_mesh.py --reset
```

---

## 9. Database

### SQLite Schema

**`reports` table**
| Column | Type | Description |
|--------|------|-------------|
| id | Integer PK | Auto-increment |
| timestamp | DateTime | Submission time |
| text_message | String | Citizen's description |
| image_path | String | Path to uploaded photo |
| latitude, longitude | Float | GPS coordinates |
| text_score | Float | NLP score 0–10 |
| image_score | Float | Vision score 0–10 |
| location_risk | Float | Cluster score 0–10 |
| final_priority | Float | Weighted final score 0–10 |
| nlp_category | String | DistilBERT classification |
| nlp_confidence | Float | Model confidence 0–1 |
| image_class | String | ResNet50 classification |
| image_confidence | Float | Vision confidence 0–1 |
| ai_reasoning | JSON | Full score breakdown |
| status | String | pending / dispatched / resolved |

**`dispatch_log` table** — records when and who dispatched each report

### Reset Database
```bash
rm backend/disaster_reports.db
# Recreates automatically on next request
```

---

## 10. How to Run Locally

### Prerequisites
- Python 3.11+ with venv set up
- Node.js 18+
- Model weights present at:
  - `ai-models/outputs/best_model.pt` (ResNet50, 210MB)
  - `model/models/distilbert_crisis_classifier/` (DistilBERT, 255MB)

### Start Everything
```bash
cd /Users/neharani/Disaster-Management-System
bash start.sh
```

This kills old processes, starts backend on port 8000 and frontend on port 3000.

### Open in Browser
| URL | What |
|-----|------|
| http://localhost:3000 | Responder dashboard |
| http://localhost:3000/citizen | Citizen report form |
| http://localhost:8000/docs | API documentation (Swagger) |

### Run the Demo Simulator (fires 20 reports)
```bash
# New terminal
source venv/bin/activate
python simulator/generate_reports.py
```

Watch 20 reports appear on the dashboard in real time, ranked by AI priority.

### Run Phase 2 Mesh Demo
```bash
# New terminal
source venv/bin/activate
python -m uvicorn mesh.relay:app --port 8001 --reload

# Then run the full demo
python mesh/demo_mesh.py --reset
```

### Clear All Reports
```bash
rm backend/disaster_reports.db
# Refresh browser
```

---

## 11. Deployment

### Why Local for Now
The system requires ~1GB RAM to load both PyTorch models (DistilBERT: 500MB + ResNet50: 200MB). Render's free tier only provides 512MB. For production deployment, a minimum of 2GB RAM is needed.

### Recommended for Real Deployment
- **Railway** ($5/month free credit, up to 8GB RAM)
- **Google Cloud Run** (pay-per-request, generous free tier, up to 32GB RAM)

### What's Already Set Up
- `render.yaml` — Blueprint for one-click deploy (both services)
- `frontend/` — Vite build, environment-aware API URLs via `VITE_API_URL`
- `backend/runtime.txt` — pins Python 3.11
- `backend/download_models.py` — pre-downloads model weights at build time

---

## 12. Exhibitor Guide — How to Explain the Project

### The One-Sentence Pitch
*"We built an AI system that reads disaster reports from citizens, ranks them by how urgent they are, and shows emergency responders a live map — in real time, with no human triage needed."*

---

### The 2-Minute Demo Script

**Open the dashboard** (http://localhost:3000 — show the empty state)

> "This is what emergency responders see. Right now it's empty. Watch what happens."

**Run the simulator** (`python simulator/generate_reports.py` in Terminal 2)

> "I just fired 20 citizen reports to the system simultaneously. Watch."

*Reports appear live on the dashboard, sorted by priority*

> "The AI read all 20 messages in under a second and ranked them — no human involved. The red ones at the top are people trapped or injured. The green ones at the bottom are minor."

**Click the top report**

> "Every report shows exactly how the AI made its decision. This one got a 9.2 out of 10. The text said 'building collapsed, people trapped' — DistilBERT classified that as the highest emergency category with 94% confidence. The photo showed a collapsed building — ResNet50 confirmed it. And there were 3 other reports within 500 meters, so the location risk score pushed it even higher."

**Show the map**

> "The map shows clusters. Dark red = multiple critical reports in the same area. Responders can see at a glance where to deploy teams."

**Submit a live report** (go to http://localhost:3000/citizen)

> "I'm going to type: '3 people trapped, building collapsed on Main St' and submit."

*Show it appearing at the top of the list instantly*

> "One second. It's already ranked #1."

**Phase 2 demo** (if time allows)

> "Now what happens when the internet goes down? During Katrina, during the Turkey earthquake, the internet was the first thing that failed."

*Start the relay node, submit a report at localhost:8001*

> "Citizens connect to this over local WiFi — no internet needed. Reports queue here. The moment connectivity returns, everything syncs to the main hub. Same AI. Same dashboard. The infrastructure failure doesn't stop the triage."

---

### Common Questions & Answers

**Q: What data did you train on?**
> "For the text model, we used CrisisNLP — a dataset of real tweets from actual disasters including the 2010 Haiti earthquake, 2013 Pakistan floods, and 2015 Nepal earthquake. For the image model, we used AIDER — aerial and ground-level disaster photos. Both are research datasets used by emergency management researchers."

**Q: How accurate is it?**
> "The text model (DistilBERT) achieves over 85% accuracy on the test set. The image model (ResNet50) reaches about 88% validation accuracy. More importantly, the hybrid approach — combining AI with keyword matching — means it never misses an obvious emergency even if the model is uncertain."

**Q: What if the AI is wrong?**
> "The AI scores help responders prioritize — it's a decision support tool, not a replacement. Every responder still reviews the report before dispatching. The AI reasoning panel shows exactly why a score was given, so responders can override it. A human is always in the loop."

**Q: Why DistilBERT and not GPT?**
> "DistilBERT runs locally on CPU in milliseconds. GPT requires an API call, costs money, adds latency, and fails if the internet is down. For emergency response — especially our offline Phase 2 — you need something that runs on-device instantly."

**Q: What does the priority score mean exactly?**
> "It's a 0–10 scale. Above 8 is CRITICAL — respond immediately. 6–8 is HIGH. 4–6 is MEDIUM. Below 4 is LOW. The formula weights text classification at 60%, image damage at 30%, and location clustering at 10%. If no image is submitted, text gets 80% weight."

**Q: Could this be used in a real disaster?**
> "Yes — that's the goal. The Phase 2 mesh network addresses the biggest deployment challenge: infrastructure failure. The system is designed to run on a $35 Raspberry Pi at a disaster site. Citizens connect over a local hotspot, reports queue locally, and sync when any connectivity is available."

---

### Technical Terms — Simple Explanations

| Term | Simple Explanation |
|------|-------------------|
| DistilBERT | A language AI trained on billions of sentences — it understands what words mean in context, not just keywords |
| ResNet50 | An image AI that learned to recognize objects from 1.2 million photos — we retrained it to recognize disaster damage |
| Transfer Learning | Using an AI that already knows the basics (edges, shapes, grammar) and teaching it something specific — like a doctor specializing after med school |
| Fine-tuning | Adjusting a pre-trained model on your specific data — only the last few layers change |
| WebSocket | A persistent connection between browser and server — instead of the browser asking "any new reports?" every few seconds, the server pushes updates instantly |
| Priority Engine | The formula that combines NLP score + vision score + location clustering into one 0–10 number |
| Mesh Network | Devices talking to each other directly over WiFi without needing the internet |

---

*Built for Imagine RIT 2026 — Rochester Institute of Technology*
*GitHub: https://github.com/gsam99/Disaster-Management-System (branch: feature/ai-models)*
