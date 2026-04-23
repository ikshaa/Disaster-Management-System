import json
import math
from sqlalchemy.orm import Session
from .schemas import Report, DispatchLog


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def create_report(db: Session, data: dict) -> Report:
    report = Report(**data)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_report(db: Session, report_id: int) -> Report | None:
    return db.query(Report).filter(Report.id == report_id).first()


def get_reports(db: Session, status: str | None = None, limit: int = 50) -> list[Report]:
    q = db.query(Report)
    if status:
        q = q.filter(Report.status == status)
    return q.order_by(Report.timestamp.desc()).limit(limit).all()


def get_prioritized(db: Session) -> list[Report]:
    return db.query(Report).order_by(Report.final_priority.desc()).all()


def update_report(db: Session, report_id: int, updates: dict) -> Report | None:
    report = get_report(db, report_id)
    if not report:
        return None
    for k, v in updates.items():
        setattr(report, k, v)
    db.commit()
    db.refresh(report)
    return report


def dispatch_report(db: Session, report_id: int, responder_id: str, notes: str = "") -> Report | None:
    report = update_report(db, report_id, {"status": "dispatched"})
    if not report:
        return None
    log = DispatchLog(report_id=report_id, responder_id=responder_id, notes=notes)
    db.add(log)
    db.commit()
    return report


def count_nearby_reports(db: Session, lat: float, lng: float, radius_m: float = 500) -> int:
    reports = db.query(Report).filter(
        Report.latitude.isnot(None),
        Report.longitude.isnot(None),
    ).all()
    return sum(
        1 for r in reports
        if haversine_m(lat, lng, r.latitude, r.longitude) <= radius_m
    )


def get_hotspots(db: Session) -> list[dict]:
    reports = db.query(Report).filter(
        Report.latitude.isnot(None),
        Report.longitude.isnot(None),
    ).all()

    processed = set()
    clusters = []

    for i, r in enumerate(reports):
        if i in processed:
            continue
        nearby_idx = [
            j for j, s in enumerate(reports)
            if j != i and j not in processed
            and haversine_m(r.latitude, r.longitude, s.latitude, s.longitude) <= 500
        ]
        group = [i] + nearby_idx
        for idx in group:
            processed.add(idx)

        group_reports = [reports[idx] for idx in group]
        center_lat = sum(x.latitude for x in group_reports) / len(group_reports)
        center_lng = sum(x.longitude for x in group_reports) / len(group_reports)
        avg_priority = sum(x.final_priority for x in group_reports) / len(group_reports)

        clusters.append({
            "center_lat": round(center_lat, 6),
            "center_lng": round(center_lng, 6),
            "report_count": len(group_reports),
            "avg_priority": round(avg_priority, 2),
        })

    return clusters


def get_stats(db: Session) -> dict:
    total = db.query(Report).count()
    pending = db.query(Report).filter(Report.status == "pending").count()
    dispatched = db.query(Report).filter(Report.status == "dispatched").count()
    resolved = db.query(Report).filter(Report.status == "resolved").count()
    critical = db.query(Report).filter(Report.final_priority >= 8.0).count()
    return {
        "total": total,
        "pending": pending,
        "dispatched": dispatched,
        "resolved": resolved,
        "critical": critical,
    }
