from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    text_message = Column(Text, nullable=False)
    image_path = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    text_score = Column(Float, default=0.0)
    image_score = Column(Float, default=0.0)
    location_risk = Column(Float, default=0.0)
    final_priority = Column(Float, default=0.0)

    nlp_category = Column(String, nullable=True)
    nlp_confidence = Column(Float, nullable=True)
    image_class = Column(String, nullable=True)
    image_confidence = Column(Float, nullable=True)

    ai_reasoning = Column(Text, nullable=True)  # JSON string
    status = Column(String, default="pending")  # pending / dispatched / resolved


class DispatchLog(Base):
    __tablename__ = "dispatch_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, nullable=False)
    dispatched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    responder_id = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
