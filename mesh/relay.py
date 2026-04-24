"""
Mesh Relay Node — Phase 2 of AI Disaster Response Coordinator

Runs on edge devices (laptops, Raspberry Pi, phone hotspots).
Citizens connect via local WiFi and submit reports — no internet needed.
When the relay gains connectivity to the hub, it syncs all queued reports.

Usage:
    uvicorn mesh.relay:app --port 8001 --reload
    # or from project root:
    python -m uvicorn mesh.relay:app --port 8001
"""

import io
import json
import os
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

DB_PATH = os.path.join(os.path.dirname(__file__), "relay_queue.db")
DEFAULT_HUB_URL = os.getenv("HUB_URL", "http://localhost:8000")


# ── Database ──────────────────────────────────────────────────────────────────

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS queued_reports (
            id          TEXT PRIMARY KEY,
            received_at TEXT NOT NULL,
            text_message TEXT NOT NULL,
            latitude    REAL,
            longitude   REAL,
            image_data  BLOB,
            image_filename TEXT,
            synced      INTEGER DEFAULT 0,
            synced_at   TEXT
        )
    """)
    conn.commit()
    conn.close()


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Mesh Relay Node", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Citizen HTML form (served locally — no internet needed) ───────────────────

CITIZEN_FORM_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Disaster Report — Mesh Node</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
         background:#0f172a;color:#f1f5f9;min-height:100vh;display:flex;
         align-items:center;justify-content:center;padding:1rem}
    .card{background:#1e293b;border:1px solid #334155;border-radius:12px;
          width:100%;max-width:420px;overflow:hidden}
    .header{background:#dc2626;padding:1rem 1.25rem}
    .header h1{font-size:1.1rem;font-weight:700;letter-spacing:.05em}
    .header p{font-size:.75rem;opacity:.85;margin-top:.2rem}
    .badge{display:inline-flex;align-items:center;gap:.4rem;font-size:.7rem;
           padding:.25rem .6rem;border-radius:999px;margin-top:.5rem;font-weight:600}
    .badge.relay{background:#1e3a5f;color:#60a5fa}
    .body{padding:1.25rem;display:flex;flex-direction:column;gap:.9rem}
    label{font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;color:#94a3b8;display:block;margin-bottom:.3rem}
    textarea,input[type=text],input[type=number]{width:100%;background:#0f172a;
      border:1px solid #334155;border-radius:6px;padding:.6rem .75rem;
      color:#f1f5f9;font-size:.9rem;outline:none;transition:border-color .2s}
    textarea:focus,input:focus{border-color:#dc2626}
    textarea{resize:none;height:90px}
    .row{display:grid;grid-template-columns:1fr 1fr;gap:.6rem}
    .loc-btn{font-size:.7rem;color:#60a5fa;text-decoration:underline;
             background:none;border:none;cursor:pointer;margin-top:.2rem;padding:0}
    input[type=file]{color:#94a3b8;font-size:.8rem}
    input[type=file]::file-selector-button{background:#334155;border:none;color:#f1f5f9;
      padding:.3rem .7rem;border-radius:4px;cursor:pointer;font-size:.75rem;margin-right:.5rem}
    .submit-btn{width:100%;padding:.75rem;background:#dc2626;border:none;border-radius:8px;
      color:#fff;font-weight:700;font-size:.95rem;cursor:pointer;transition:background .2s}
    .submit-btn:hover{background:#b91c1c}
    .submit-btn:disabled{opacity:.5;cursor:not-allowed}
    .status{font-size:.8rem;padding:.5rem .75rem;border-radius:6px;text-align:center;display:none}
    .status.success{background:#14532d;color:#86efac;display:block}
    .status.error{background:#450a0a;color:#fca5a5;display:block}
    .queue-info{font-size:.7rem;color:#64748b;text-align:center}
  </style>
</head>
<body>
<div class="card">
  <div class="header">
    <h1>🆘 Submit Disaster Report</h1>
    <p>This device operates offline — your report is stored locally and will sync to the response hub when connectivity is available.</p>
    <span class="badge relay">📡 MESH RELAY NODE</span>
  </div>
  <div class="body">
    <div id="statusMsg" class="status"></div>
    <div>
      <label>Describe the situation *</label>
      <textarea id="text" placeholder="e.g. Building collapsed, 3 people trapped inside..."></textarea>
    </div>
    <div class="row">
      <div>
        <label>Latitude</label>
        <input type="number" id="lat" placeholder="43.0831" step="0.000001"/>
      </div>
      <div>
        <label>Longitude</label>
        <input type="number" id="lng" placeholder="-76.1474" step="0.000001"/>
      </div>
    </div>
    <button class="loc-btn" onclick="getLocation()">📍 Use my location</button>
    <div>
      <label>Photo of disaster area (optional)</label>
      <input type="file" id="image" accept="image/*" capture="environment"/>
    </div>
    <button class="submit-btn" id="submitBtn" onclick="submitReport()">Submit Report</button>
    <div class="queue-info" id="queueInfo">Loading queue status...</div>
  </div>
</div>

<script>
async function getLocation() {
  if (!navigator.geolocation) return;
  navigator.geolocation.getCurrentPosition(pos => {
    document.getElementById('lat').value = pos.coords.latitude.toFixed(6);
    document.getElementById('lng').value = pos.coords.longitude.toFixed(6);
  });
}

async function loadStatus() {
  try {
    const r = await fetch('/status');
    const d = await r.json();
    document.getElementById('queueInfo').textContent =
      `Queue: ${d.pending} pending · ${d.synced} synced · ${d.total} total reports`;
  } catch(e) { document.getElementById('queueInfo').textContent = 'Relay node active'; }
}

async function submitReport() {
  const text = document.getElementById('text').value.trim();
  if (!text) { showStatus('Please describe the situation.', 'error'); return; }

  const btn = document.getElementById('submitBtn');
  btn.disabled = true;
  btn.textContent = 'Submitting...';

  const lat = document.getElementById('lat').value.trim();
  const lng = document.getElementById('lng').value.trim();
  if (!lat || !lng) {
    showStatus('Location is required. Click "Use my location" or enter coordinates manually.', 'error');
    btn.disabled = false; btn.textContent = 'Submit Report'; return;
  }

  const fd = new FormData();
  fd.append('text_message', text);
  fd.append('latitude', lat);
  fd.append('longitude', lng);
  const img = document.getElementById('image').files[0];
  if (img) fd.append('image', img);

  try {
    const r = await fetch('/submit', { method: 'POST', body: fd });
    const d = await r.json();
    showStatus(`✓ Report queued (ID: ${d.queue_id}). It will sync to the response hub when connected.`, 'success');
    document.getElementById('text').value = '';
    document.getElementById('image').value = '';
    loadStatus();
  } catch(e) {
    showStatus('Error submitting. Please try again.', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Submit Report';
  }
}

function showStatus(msg, type) {
  const el = document.getElementById('statusMsg');
  el.textContent = msg;
  el.className = 'status ' + type;
  setTimeout(() => { el.className = 'status'; }, 6000);
}

loadStatus();
setInterval(loadStatus, 10000);
// Auto-detect location on page load
getLocation();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def citizen_form():
    return CITIZEN_FORM_HTML


# ── Report submission from citizens ──────────────────────────────────────────

@app.post("/submit")
async def submit_report(
    text_message: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    image: Optional[UploadFile] = File(None),
):
    image_data = None
    image_filename = None

    if image and image.filename:
        raw = await image.read()
        # Compress to max 800px to keep SQLite BLOB manageable
        try:
            from PIL import Image as PILImage
            img = PILImage.open(io.BytesIO(raw)).convert("RGB")
            img.thumbnail((800, 800))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            image_data = buf.getvalue()
            image_filename = image.filename
        except Exception:
            image_data = raw
            image_filename = image.filename

    report_id = str(uuid.uuid4())
    received_at = datetime.now(timezone.utc).isoformat()

    conn = get_conn()
    conn.execute(
        "INSERT INTO queued_reports (id, received_at, text_message, latitude, longitude, image_data, image_filename) VALUES (?,?,?,?,?,?,?)",
        (report_id, received_at, text_message, latitude, longitude, image_data, image_filename),
    )
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM queued_reports WHERE synced=0").fetchone()[0]
    conn.close()

    return {"status": "queued", "queue_id": report_id, "pending_count": count}


# ── Sync queued reports to main hub ──────────────────────────────────────────

@app.post("/sync")
async def sync_to_hub(hub_url: str = DEFAULT_HUB_URL):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM queued_reports WHERE synced=0 ORDER BY received_at"
    ).fetchall()

    synced, failed = 0, 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        for row in rows:
            try:
                data = {
                    "text_message": row["text_message"],
                }
                if row["latitude"] is not None:
                    data["latitude"] = str(row["latitude"])
                if row["longitude"] is not None:
                    data["longitude"] = str(row["longitude"])

                files = None
                if row["image_data"]:
                    files = {"image": (row["image_filename"] or "image.jpg", row["image_data"], "image/jpeg")}

                resp = await client.post(
                    f"{hub_url}/api/v1/reports",
                    data=data,
                    files=files,
                )
                resp.raise_for_status()

                conn.execute(
                    "UPDATE queued_reports SET synced=1, synced_at=? WHERE id=?",
                    (datetime.now(timezone.utc).isoformat(), row["id"]),
                )
                conn.commit()
                synced += 1

            except Exception as e:
                failed += 1
                print(f"Failed to sync report {row['id']}: {e}")

    conn.close()
    return {"synced": synced, "failed": failed, "hub_url": hub_url}


# ── Status & management ───────────────────────────────────────────────────────

@app.get("/status")
def get_status():
    conn = get_conn()
    pending = conn.execute("SELECT COUNT(*) FROM queued_reports WHERE synced=0").fetchone()[0]
    synced = conn.execute("SELECT COUNT(*) FROM queued_reports WHERE synced=1").fetchone()[0]
    conn.close()
    return {"pending": pending, "synced": synced, "total": pending + synced}


@app.get("/queue")
def get_queue():
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, received_at, text_message, latitude, longitude, image_filename, synced, synced_at FROM queued_reports ORDER BY received_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/reset")
def reset_queue():
    conn = get_conn()
    conn.execute("DELETE FROM queued_reports")
    conn.commit()
    conn.close()
    return {"status": "queue cleared"}
