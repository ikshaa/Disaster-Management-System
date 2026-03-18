BASE_SCORES: dict[str, int] = {
    "people trapped":          10,
    "injured people":           9,
    "infrastructure collapse":  8,
    "fire damage":              8,
    "request for rescue":       7,
    "flood damage":             6,
    "low priority situation":   2,
}

DEFAULT_BASE_SCORE = 2


def get_base_score(category: str) -> int:
    return BASE_SCORES.get(category, DEFAULT_BASE_SCORE)


def compute_text_score(category: str, confidence: float) -> float:
    base  = get_base_score(category)
    score = base * confidence
    return round(score, 1)


def score_report(nlp_result: dict) -> dict:
    category   = nlp_result.get("category", "")
    confidence = nlp_result.get("confidence", 0.0)
    return {
        **nlp_result,
        "text_score": compute_text_score(category, confidence),
    }


if __name__ == "__main__":
    print("\nScoring table verification")
    print("-" * 40)
    print(f"{'Category':<28} {'Base':>5}  {'Conf':>5}  {'Score':>6}")
    print("-" * 40)

    test_cases = [
        ("people trapped",         0.92),
        ("people trapped",         0.88),
        ("injured people",         0.75),
        ("infrastructure collapse", 0.81),
        ("fire damage",            0.65),
        ("request for rescue",     0.70),
        ("flood damage",           0.55),
        ("low priority situation", 0.90),
    ]

    for category, confidence in test_cases:
        base  = get_base_score(category)
        score = compute_text_score(category, confidence)
        print(f"  {category:<26} {base:>5}  {confidence:>5.2f}  {score:>6.1f}")
