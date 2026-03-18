import sys
import os
from collections import Counter

import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

for _pkg in ("punkt", "punkt_tab", "stopwords"):
    nltk.download(_pkg, quiet=True)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.ai.text_scoring import compute_text_score

_stemmer    = PorterStemmer()
_stop_words = set(stopwords.words("english"))

_RAW_KEYWORDS: dict[str, list[str]] = {
    "people trapped": [
        "trapped", "trap", "stuck", "buried", "bury", "rubble",
        "pinned", "underneath", "entrap", "confined", "crushed",
        "inside", "cannot", "escape",
    ],
    "injured people": [
        "injured", "injury", "hurt", "wounded", "wound", "bleeding",
        "blood", "dead", "death", "killed", "kill", "casualty",
        "casualties", "victim", "hospitalized", "medical",
    ],
    "fire damage": [
        "fire", "burning", "burn", "flames", "flame", "smoke",
        "wildfire", "blaze", "arson", "firefighter", "scorched", "ignite",
    ],
    "flood damage": [
        "flood", "flooding", "flooded", "inundated", "submerged",
        "overflow", "hurricane", "typhoon", "tsunami", "rain",
        "rising", "water", "surge",
    ],
    "infrastructure collapse": [
        "bridge", "road", "highway", "power", "electricity",
        "utility", "dam", "infrastructure", "collapsed", "collapse",
        "structure", "building", "damaged", "destroyed",
    ],
    "request for rescue": [
        "rescue", "help", "sos", "emergency", "stranded", "evacuate",
        "evacuation", "aid", "assistance", "save", "respond", "respond",
    ],
    "low priority situation": [
        "prayer", "prayers", "donate", "donation", "volunteer",
        "update", "information", "awareness", "sympathy",
        "condolences", "thoughts", "news",
    ],
}

STEMMED_KEYWORDS: dict[str, set[str]] = {
    cat: {_stemmer.stem(w) for w in words}
    for cat, words in _RAW_KEYWORDS.items()
}

def preprocess(text: str) -> list[str]:
    tokens = word_tokenize(text.lower())
    return [
        _stemmer.stem(t)
        for t in tokens
        if t.isalpha() and t not in _stop_words
    ]


def classify(text: str) -> dict:
    token_counts = Counter(preprocess(text))

    raw_scores: dict[str, int] = {
        cat: sum(token_counts[kw] for kw in keywords if kw in token_counts)
        for cat, keywords in STEMMED_KEYWORDS.items()
    }

    total = sum(raw_scores.values())

    if total == 0:
        normalized: dict[str, float] = {cat: 0.0 for cat in raw_scores}
        normalized["low priority situation"] = 1.0
    else:
        normalized = {
            cat: round(score / total, 4)
            for cat, score in raw_scores.items()
        }

    sorted_scores = dict(
        sorted(normalized.items(), key=lambda x: x[1], reverse=True)
    )
    top_label = next(iter(sorted_scores))
    top_score = sorted_scores[top_label]

    return {
        "category":   top_label,
        "confidence": top_score,
        "all_scores": sorted_scores,
    }


def analyze(text) -> dict:
    if isinstance(text, dict):
        text = text.get("text", "")

    result = classify(str(text))
    result["text_score"] = compute_text_score(
        result["category"],
        result["confidence"],
    )
    return result


if __name__ == "__main__":
    examples = [
        "Two people trapped in a collapsed building",
        "There is a building collapse and people trapped inside",
        "Person trapped under collapsed building near bridge",
        "Fire spreading through apartment complex on Main St",
        "Flooding has damaged the highway overpass",
        "We need immediate rescue, people are stranded on the roof",
        "Please keep the victims in your prayers",
    ]

    print("\n" + "=" * 65)
    print("NLP Classifier (NLTK) — smoke test")
    print("=" * 65)

    for msg in examples:
        r = analyze(msg)
        print(f"\nInput : {msg}")
        print(f"  category  : {r['category']}")
        print(f"  confidence: {r['confidence']:.2%}")
        print(f"  text_score: {r['text_score']}")
        print("  all scores:")
        for lbl, sc in r["all_scores"].items():
            bar = "█" * int(sc * 20)
            print(f"    {sc:.2f}  {bar:<20}  {lbl}")
