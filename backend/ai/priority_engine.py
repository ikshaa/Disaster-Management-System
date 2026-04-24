import math
from sqlalchemy.orm import Session
from db.crud import count_nearby_reports


def compute_location_risk(db: Session, lat: float | None, lng: float | None) -> float:
    if lat is None or lng is None:
        return 0.0
    nearby = count_nearby_reports(db, lat, lng, radius_m=500)
    if nearby >= 5:
        return 10.0
    elif nearby >= 3:
        return 8.0
    elif nearby >= 2:
        return 5.0
    elif nearby >= 1:
        return 2.0
    return 0.0


def compute_final_priority(text_score: float, image_score: float, location_risk: float) -> float:
    if image_score == 0.0:
        # No image submitted — redistribute image weight to text and location
        score = (text_score * 0.8) + (location_risk * 0.2)
    else:
        score = (text_score * 0.6) + (image_score * 0.3) + (location_risk * 0.1)
    return round(min(score, 10.0), 2)


def build_ai_reasoning(
    text_message: str,
    nlp_result: dict,
    vision_result: dict | None,
    location_risk: float,
    nearby_count: int,
    final_priority: float,
) -> dict:
    reasoning = {
        "nlp_class": nlp_result.get("category"),
        "nlp_confidence": nlp_result.get("confidence"),
        "text_score": nlp_result.get("text_score"),
        "image_damage": vision_result.get("image_class") if vision_result else "no image",
        "image_severity": vision_result.get("severity") if vision_result else "N/A",
        "image_score": vision_result.get("image_score", 0.0) if vision_result else 0.0,
        "image_confidence": vision_result.get("confidence") if vision_result else None,
        "location_cluster": f"{nearby_count} report(s) within 500m" + (" → risk multiplier active" if nearby_count >= 2 else ""),
        "location_risk": location_risk,
        "score_breakdown": {
            "text_score": nlp_result.get("text_score"),
            "text_weight": 0.6 if vision_result else 0.8,
            "image_score": vision_result.get("image_score", 0.0) if vision_result else 0.0,
            "image_weight": 0.3 if vision_result else 0.0,
            "location_risk": location_risk,
            "location_weight": 0.1 if vision_result else 0.2,
            "final_priority": final_priority,
        },
        "all_nlp_scores": nlp_result.get("all_scores", {}),
    }
    return reasoning
