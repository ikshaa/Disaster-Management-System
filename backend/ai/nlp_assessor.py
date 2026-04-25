import os
import re
import logging

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(__file__)
DISTILBERT_DIR = os.path.abspath(os.path.join(BASE_DIR, "../../model/models/distilbert_crisis_classifier"))
HF_REPO = "nehagdd/rescue-ai-models"


def _ensure_distilbert_weights():
    marker = os.path.join(DISTILBERT_DIR, "model.safetensors")
    if os.path.exists(marker):
        return
    logger.info("DistilBERT weights not found locally — downloading from Hugging Face...")
    from huggingface_hub import snapshot_download
    snapshot_download(
        repo_id=HF_REPO,
        allow_patterns="distilbert/*",
        local_dir=os.path.dirname(DISTILBERT_DIR),
    )
    # snapshot_download saves to local_dir/distilbert/ — rename to match expected path
    downloaded_dir = os.path.join(os.path.dirname(DISTILBERT_DIR), "distilbert")
    if os.path.isdir(downloaded_dir) and not os.path.isdir(DISTILBERT_DIR):
        import shutil
        shutil.move(downloaded_dir, DISTILBERT_DIR)
    logger.info("DistilBERT weights downloaded")

LABELS = [
    "people trapped",
    "injured people",
    "fire damage",
    "flood damage",
    "infrastructure collapse",
    "request for rescue",
    "low priority situation",
]

BASE_SCORES = {
    "people trapped": 10,
    "injured people": 9,
    "infrastructure collapse": 8,
    "fire damage": 8,
    "request for rescue": 7,
    "flood damage": 6,
    "low priority situation": 2,
}

KEYWORD_MAP = {
    "people trapped": ["trapped", "trap", "stuck", "buried", "cannot move", "can't move"],
    "injured people": ["injured", "injury", "hurt", "wounded", "bleeding", "unconscious", "dying", "severe"],
    "fire damage": ["fire", "burning", "burn", "flames", "smoke", "blaze"],
    "flood damage": ["flood", "flooding", "flooded", "inundated", "submerged", "water rising"],
    "infrastructure collapse": ["collapsed", "collapse", "building down", "structural", "bridge", "road damage"],
    "request for rescue": ["rescue", "help", "sos", "emergency", "need help", "save us"],
    "low priority situation": ["minor", "small", "debris", "road", "prayer", "donate"],
}

_tokenizer = None
_nlp_model = None


def _load_bert():
    global _tokenizer, _nlp_model
    if _nlp_model is None:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        import torch
        _ensure_distilbert_weights()
        _tokenizer = AutoTokenizer.from_pretrained(DISTILBERT_DIR)
        _nlp_model = AutoModelForSequenceClassification.from_pretrained(DISTILBERT_DIR)
        _nlp_model.eval()
        logger.info("DistilBERT NLP model loaded")
    return _tokenizer, _nlp_model


def _keyword_fallback(text: str) -> dict:
    text_lower = text.lower()
    scores = {label: 0 for label in LABELS}
    for label, keywords in KEYWORD_MAP.items():
        scores[label] = sum(1 for kw in keywords if kw in text_lower)
    total = sum(scores.values())
    if total == 0:
        top_label = "low priority situation"
        confidence = 0.5
    else:
        top_label = max(scores, key=scores.get)
        top_ratio = scores[top_label] / total
        # Scale confidence: more dominant + more matches = higher confidence
        match_bonus = min(0.2, scores[top_label] * 0.05)
        confidence = round(min(0.95, 0.55 + top_ratio * 0.35 + match_bonus), 4)
    return {"category": top_label, "confidence": confidence, "all_scores": scores}


def classify_text(text: str) -> dict:
    # Always run keyword fallback as a safety net
    kw = _keyword_fallback(text)

    try:
        import torch
        tokenizer, model = _load_bert()
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=128, padding=True)
        with torch.no_grad():
            logits = model(**inputs).logits[0]
            probs = torch.softmax(logits, dim=0)

        id2label = model.config.id2label
        score_pairs = sorted(
            [(id2label[i], round(probs[i].item(), 4)) for i in range(len(probs))],
            key=lambda x: x[1], reverse=True
        )
        bert_label, bert_conf = score_pairs[0]
        all_scores = dict(score_pairs)

        # Hybrid: if DistilBERT downgrades to low-priority but keywords clearly say otherwise, trust keywords
        kw_priority = BASE_SCORES.get(kw["category"], 2)
        bert_priority = BASE_SCORES.get(bert_label, 2)
        kw_has_signal = kw["category"] != "low priority situation" and kw["confidence"] > 0.6

        if bert_priority < kw_priority and kw_has_signal:
            top_label, top_conf = kw["category"], kw["confidence"]
        else:
            top_label, top_conf = bert_label, bert_conf

    except Exception as e:
        logger.warning(f"DistilBERT failed ({e}), using keyword fallback")
        top_label, top_conf = kw["category"], kw["confidence"]
        all_scores = kw["all_scores"]

    base_score = BASE_SCORES.get(top_label, 2)
    text_score = round(base_score * top_conf, 1)

    return {
        "category": top_label,
        "confidence": top_conf,
        "text_score": text_score,
        "all_scores": all_scores,
    }
