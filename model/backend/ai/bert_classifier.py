import os
import sys
import json
import argparse

import torch
from sklearn.model_selection import train_test_split
from torch.utils.data import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.ai.preprocess_dataset import clean_text, load_all_tweets, map_label
from backend.ai.text_scoring import compute_text_score

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
DEFAULT_MODEL_NAME = "distilbert-base-uncased"
DEFAULT_MODEL_DIR = os.path.join(PROJECT_ROOT, "models", "distilbert_crisis_classifier")
LABELS = [
    "people trapped",
    "injured people",
    "fire damage",
    "flood damage",
    "infrastructure collapse",
    "request for rescue",
    "low priority situation",
]
LABEL_TO_ID = {label: idx for idx, label in enumerate(LABELS)}
ID_TO_LABEL = {idx: label for label, idx in LABEL_TO_ID.items()}
_MODEL_CACHE: dict[tuple[str, str], tuple[AutoTokenizer, AutoModelForSequenceClassification]] = {}


class CrisisTextDataset(Dataset):
    def __init__(self, texts: list[str], labels: list[int], tokenizer, max_length: int):
        self.encodings = tokenizer(
            texts,
            truncation=True,
            padding=True,
            max_length=max_length,
        )
        self.labels = labels

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        item = {
            key: torch.tensor(value[idx])
            for key, value in self.encodings.items()
        }
        item["labels"] = torch.tensor(self.labels[idx])
        return item


def _normalize_text(text) -> str:
    if isinstance(text, dict):
        text = text.get("text", "")
    return clean_text(str(text))


def _load_model_assets(model_dir: str = DEFAULT_MODEL_DIR):
    cache_key = (os.path.abspath(model_dir), DEFAULT_MODEL_NAME)
    if cache_key not in _MODEL_CACHE:
        if not os.path.isdir(model_dir):
            raise FileNotFoundError(
                f"DistilBERT model directory not found: {model_dir}. Train the model first."
            )
        tokenizer = AutoTokenizer.from_pretrained(model_dir)
        model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        model.eval()
        _MODEL_CACHE[cache_key] = (tokenizer, model)
    return _MODEL_CACHE[cache_key]


def classify(text, model_dir: str = DEFAULT_MODEL_DIR, max_length: int = 128) -> dict:
    cleaned_text = _normalize_text(text)
    tokenizer, model = _load_model_assets(model_dir)
    encoded = tokenizer(
        cleaned_text,
        return_tensors="pt",
        truncation=True,
        max_length=max_length,
    )
    with torch.no_grad():
        logits = model(**encoded).logits[0]
        probabilities = torch.softmax(logits, dim=0)

    score_pairs = sorted(
        (
            (model.config.id2label[idx], round(probabilities[idx].item(), 4))
            for idx in range(len(probabilities))
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    top_label, top_score = score_pairs[0]
    return {
        "category": top_label,
        "confidence": top_score,
        "all_scores": dict(score_pairs),
    }


def analyze(text, model_dir: str = DEFAULT_MODEL_DIR, max_length: int = 128) -> dict:
    result = classify(text, model_dir=model_dir, max_length=max_length)
    result["text_score"] = compute_text_score(
        result["category"],
        result["confidence"],
    )
    return result


def _load_training_examples() -> tuple[list[str], list[int]]:
    rows = load_all_tweets()
    texts = []
    labels = []
    for row in rows:
        category = map_label(row["raw_label"])
        texts.append(clean_text(row["original_text"]))
        labels.append(LABEL_TO_ID[category])
    return texts, labels


def train(
    output_dir: str = DEFAULT_MODEL_DIR,
    model_name: str = DEFAULT_MODEL_NAME,
    epochs: int = 3,
    batch_size: int = 8,
    max_length: int = 128,
    learning_rate: float = 2e-5,
    test_size: float = 0.1,
) -> None:
    texts, labels = _load_training_examples()
    train_texts, eval_texts, train_labels, eval_labels = train_test_split(
        texts,
        labels,
        test_size=test_size,
        random_state=42,
        stratify=labels,
    )

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    train_dataset = CrisisTextDataset(train_texts, train_labels, tokenizer, max_length)
    eval_dataset = CrisisTextDataset(eval_texts, eval_labels, tokenizer, max_length)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=len(LABELS),
        id2label=ID_TO_LABEL,
        label2id=LABEL_TO_ID,
    )

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_strategy="epoch",
        load_best_model_at_end=False,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
    )

    trainer.train()
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    metadata = {
        "base_model": model_name,
        "labels": LABELS,
        "train_examples": len(train_texts),
        "eval_examples": len(eval_texts),
        "max_length": max_length,
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
    }
    with open(os.path.join(output_dir, "training_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"Saved DistilBERT classifier to {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    train_parser = subparsers.add_parser("train")
    train_parser.add_argument("--output-dir", default=DEFAULT_MODEL_DIR)
    train_parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    train_parser.add_argument("--epochs", type=int, default=3)
    train_parser.add_argument("--batch-size", type=int, default=8)
    train_parser.add_argument("--max-length", type=int, default=128)
    train_parser.add_argument("--learning-rate", type=float, default=2e-5)
    train_parser.add_argument("--test-size", type=float, default=0.1)

    predict_parser = subparsers.add_parser("predict")
    predict_parser.add_argument("text")
    predict_parser.add_argument("--model-dir", default=DEFAULT_MODEL_DIR)
    predict_parser.add_argument("--max-length", type=int, default=128)

    args = parser.parse_args()

    if args.command == "train":
        train(
            output_dir=args.output_dir,
            model_name=args.model_name,
            epochs=args.epochs,
            batch_size=args.batch_size,
            max_length=args.max_length,
            learning_rate=args.learning_rate,
            test_size=args.test_size,
        )
        return

    result = analyze(
        args.text,
        model_dir=args.model_dir,
        max_length=args.max_length,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
