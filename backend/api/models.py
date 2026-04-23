from pydantic import BaseModel
from datetime import datetime
from typing import Any


class ReportResponse(BaseModel):
    id: int
    timestamp: datetime
    text_message: str
    image_path: str | None
    latitude: float | None
    longitude: float | None
    text_score: float
    image_score: float
    location_risk: float
    final_priority: float
    nlp_category: str | None
    nlp_confidence: float | None
    image_class: str | None
    image_confidence: float | None
    ai_reasoning: Any
    status: str

    class Config:
        from_attributes = True


class DispatchRequest(BaseModel):
    responder_id: str
    notes: str = ""


class StatsResponse(BaseModel):
    total: int
    pending: int
    dispatched: int
    resolved: int
    critical: int


class HotspotResponse(BaseModel):
    center_lat: float
    center_lng: float
    report_count: int
    avg_priority: float
