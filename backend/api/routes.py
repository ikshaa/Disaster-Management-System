import os
import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from db.database import get_db
from db import crud
from ai import nlp_assessor, vision_assessor
from ai.priority_engine import compute_location_risk, compute_final_priority, build_ai_reasoning
from api.models import ReportResponse, DispatchRequest, StatsResponse, HotspotResponse
from ws_manager import manager

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")


def _report_to_dict(report) -> dict:
    d = {c.name: getattr(report, c.name) for c in report.__table__.columns}
    if isinstance(d.get("ai_reasoning"), str):
        try:
            d["ai_reasoning"] = json.loads(d["ai_reasoning"])
        except Exception:
            pass
    return d


@router.post("/reports", response_model=ReportResponse)
async def create_report(
    text_message: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    # 1. Save image
    image_path = None
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1]
        filename = f"{uuid.uuid4().hex}{ext}"
        image_path = os.path.join(UPLOAD_DIR, filename)
        with open(image_path, "wb") as f:
            f.write(await image.read())

    # 2. NLP analysis
    nlp_result = nlp_assessor.classify_text(text_message)

    # 3. Vision analysis
    vision_result = None
    image_score = 0.0
    image_class = None
    image_confidence = None
    if image_path:
        vision_result = vision_assessor.analyze_image(image_path)
        image_score = vision_result["image_score"]
        image_class = vision_result["image_class"]
        image_confidence = vision_result["confidence"]

    # 4. Location risk
    nearby_count = crud.count_nearby_reports(db, latitude, longitude) if latitude and longitude else 0
    location_risk = compute_location_risk(db, latitude, longitude)

    # 5. Final priority
    final_priority = compute_final_priority(nlp_result["text_score"], image_score, location_risk)

    # 6. AI reasoning
    reasoning = build_ai_reasoning(
        text_message, nlp_result, vision_result, location_risk, nearby_count, final_priority
    )

    # 7. Save to DB
    report = crud.create_report(db, {
        "text_message": text_message,
        "image_path": image_path,
        "latitude": latitude,
        "longitude": longitude,
        "text_score": nlp_result["text_score"],
        "image_score": image_score,
        "location_risk": location_risk,
        "final_priority": final_priority,
        "nlp_category": nlp_result["category"],
        "nlp_confidence": nlp_result["confidence"],
        "image_class": image_class,
        "image_confidence": image_confidence,
        "ai_reasoning": json.dumps(reasoning),
    })

    # 8. Broadcast via WebSocket
    await manager.broadcast({"type": "new_report", "report": _report_to_dict(report)})

    d = _report_to_dict(report)
    return ReportResponse(**d)


@router.get("/reports", response_model=list[ReportResponse])
def get_reports(status: Optional[str] = None, limit: int = 50, db: Session = Depends(get_db)):
    reports = crud.get_reports(db, status=status, limit=limit)
    return [ReportResponse(**_report_to_dict(r)) for r in reports]


@router.get("/prioritized", response_model=list[ReportResponse])
def get_prioritized(db: Session = Depends(get_db)):
    reports = crud.get_prioritized(db)
    return [ReportResponse(**_report_to_dict(r)) for r in reports]


@router.get("/reports/{report_id}", response_model=ReportResponse)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = crud.get_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportResponse(**_report_to_dict(report))


@router.post("/reports/{report_id}/dispatch")
async def dispatch_report(report_id: int, body: DispatchRequest, db: Session = Depends(get_db)):
    report = crud.dispatch_report(db, report_id, body.responder_id, body.notes)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    d = _report_to_dict(report)
    await manager.broadcast({"type": "report_updated", "report": d})
    return {"success": True, "report_id": report_id}


@router.get("/hotspots", response_model=list[HotspotResponse])
def get_hotspots(db: Session = Depends(get_db)):
    return crud.get_hotspots(db)


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    return crud.get_stats(db)


# ── Phase 2: Mesh batch sync endpoint ─────────────────────────────────────────

from pydantic import BaseModel as _BaseModel


class _MeshReport(_BaseModel):
    text_message: str
    latitude: float
    longitude: float


class _MeshSyncRequest(_BaseModel):
    reports: list[_MeshReport]
    relay_id: str = "unknown"


@router.post("/mesh/sync")
async def mesh_sync(body: _MeshSyncRequest, db: Session = Depends(get_db)):
    """Accepts a batch of text-only reports from a mesh relay node."""
    processed, failed = 0, 0

    for r in body.reports:
        try:
            nlp_result = nlp_assessor.classify_text(r.text_message)
            nearby = crud.count_nearby_reports(db, r.latitude, r.longitude) if r.latitude and r.longitude else 0
            location_risk = compute_location_risk(db, r.latitude, r.longitude)
            final_priority = compute_final_priority(nlp_result["text_score"], 0.0, location_risk)
            reasoning = build_ai_reasoning(r.text_message, nlp_result, None, location_risk, nearby, final_priority)
            reasoning["source"] = f"mesh_relay:{body.relay_id}"

            report = crud.create_report(db, {
                "text_message": r.text_message,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "text_score": nlp_result["text_score"],
                "image_score": 0.0,
                "location_risk": location_risk,
                "final_priority": final_priority,
                "nlp_category": nlp_result["category"],
                "nlp_confidence": nlp_result["confidence"],
                "ai_reasoning": json.dumps(reasoning),
            })

            await manager.broadcast({"type": "new_report", "report": _report_to_dict(report)})
            processed += 1
        except Exception as e:
            failed += 1

    return {"received": len(body.reports), "processed": processed, "failed": failed, "relay_id": body.relay_id}
