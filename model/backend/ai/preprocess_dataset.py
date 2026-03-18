import os
import sys
import re
import csv
import argparse

import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

for _pkg in ("punkt", "punkt_tab", "stopwords"):
    nltk.download(_pkg, quiet=True)

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
DATA_ROOT    = os.path.join(PROJECT_ROOT, "CrisisNLP_labeled_data_crowdflower")
DEFAULT_OUT  = os.path.join(PROJECT_ROOT, "data", "preprocessed_dataset.csv")

_stemmer    = PorterStemmer()
_stop_words = set(stopwords.words("english"))

LABEL_MAP: dict[str, str] = {
    "missing_trapped_or_found_people":                   "people trapped",
    "affected_people":                                   "injured people",
    "injured_or_dead_people":                            "injured people",
    "deaths_reports":                                    "injured people",
    "infrastructure_and_utilities_damage":               "infrastructure collapse",
    "displaced_people_and_evacuations":                  "request for rescue",
    "donation_needs_or_offers_or_volunteering_services": "low priority situation",
    "caution_and_advice":                                "low priority situation",
    "prevention":                                        "low priority situation",
    "treatment":                                         "low priority situation",
    "disease_signs_or_symptoms":                         "low priority situation",
    "disease_transmission":                              "low priority situation",
    "sympathy_and_emotional_support":                    "low priority situation",
    "other_useful_information":                          "low priority situation",
    "not_related_or_irrelevant":                         "low priority situation",
}


def map_label(raw: str) -> str:
    return LABEL_MAP.get(raw.strip(), "low priority situation")


_URL_RE      = re.compile(r"https?://\S+")
_MENTION_RE  = re.compile(r"@\w+")
_HASHTAG_RE  = re.compile(r"#(\w+)")
_WHITESPACE  = re.compile(r"\s+")


def clean_text(text: str) -> str:
    text = _URL_RE.sub("", text)
    text = _MENTION_RE.sub("", text)
    text = _HASHTAG_RE.sub(r"\1", text)
    text = _WHITESPACE.sub(" ", text).strip()
    return text


def tokenize_and_stem(text: str) -> list[str]:
    tokens = word_tokenize(text.lower())
    return [
        _stemmer.stem(t)
        for t in tokens
        if t.isalpha() and t not in _stop_words
    ]


def load_all_tweets() -> list[dict]:
    rows = []
    for folder in sorted(os.listdir(DATA_ROOT)):
        folder_path = os.path.join(DATA_ROOT, folder)
        if not os.path.isdir(folder_path):
            continue
        for fname in os.listdir(folder_path):
            if not fname.endswith(".tsv"):
                continue
            fpath = os.path.join(folder_path, fname)
            with open(fpath, encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    tid   = row.get("tweet_id",   "").strip()
                    text  = row.get("tweet_text",  "").strip()
                    label = row.get("label",       "").strip()
                    if text and label:
                        rows.append({
                            "tweet_id":      tid,
                            "original_text": text,
                            "raw_label":     label,
                            "source":        folder,
                        })
    return rows


def preprocess_all(rows: list[dict]) -> list[dict]:
    processed = []
    total = len(rows)

    for i, row in enumerate(rows, 1):
        if i % 1000 == 0 or i == total:
            print(f"  Processing {i:>6}/{total} tweets …", end="\r")

        cleaned  = clean_text(row["original_text"])
        tokens   = tokenize_and_stem(cleaned)
        category = map_label(row["raw_label"])

        processed.append({
            "tweet_id":      row["tweet_id"],
            "original_text": row["original_text"],
            "cleaned_text":  cleaned,
            "tokens":        " ".join(tokens),
            "raw_label":     row["raw_label"],
            "category":      category,
            "source":        row["source"],
        })

    print()
    return processed


FIELDNAMES = [
    "tweet_id",
    "original_text",
    "cleaned_text",
    "tokens",
    "raw_label",
    "category",
    "source",
]


def save_csv(rows: list[dict], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows):,} rows → {path}")


def print_stats(rows: list[dict]) -> None:
    from collections import Counter

    print("\n── Category distribution ─────────────────────────────────")
    cat_counts = Counter(r["category"] for r in rows)
    total = len(rows)
    for cat, count in cat_counts.most_common():
        bar = "█" * int(count / total * 40)
        print(f"  {count:>6}  {bar:<40}  {cat}")

    print("\n── Source distribution ───────────────────────────────────")
    src_counts = Counter(r["source"] for r in rows)
    for src, count in src_counts.most_common():
        print(f"  {count:>6}  {src}")

    print(f"\n── Total tweets: {total:,} ──────────────────────────────\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preprocess the CrisisNLP CrowdFlower dataset with NLTK."
    )
    parser.add_argument(
        "--output", default=DEFAULT_OUT,
        help=f"Output CSV path (default: {DEFAULT_OUT})"
    )
    parser.add_argument(
        "--stats-only", action="store_true",
        help="Print dataset stats without saving the CSV"
    )
    args = parser.parse_args()

    print(f"Loading tweets from:\n  {DATA_ROOT}\n")
    raw_rows = load_all_tweets()
    print(f"Loaded {len(raw_rows):,} labeled tweets.\n")

    print("Applying NLTK preprocessing …")
    processed = preprocess_all(raw_rows)

    print_stats(processed)

    if not args.stats_only:
        save_csv(processed, args.output)


if __name__ == "__main__":
    main()
