"""Pre-downloads model weights from HuggingFace. Called during Render build."""
import os
import shutil
from huggingface_hub import hf_hub_download, snapshot_download

BASE = os.path.dirname(os.path.abspath(__file__))
RESNET_PATH = os.path.normpath(os.path.join(BASE, "..", "ai-models", "outputs", "best_model.pt"))
DISTILBERT_DIR = os.path.normpath(os.path.join(BASE, "..", "model", "models", "distilbert_crisis_classifier"))

os.makedirs(os.path.dirname(RESNET_PATH), exist_ok=True)

if not os.path.exists(RESNET_PATH):
    print("Downloading ResNet50 (210MB)...")
    cached = hf_hub_download("nehagdd/rescue-ai-models", "resnet50/best_model.pt")
    shutil.copy(cached, RESNET_PATH)
    print(f"  ResNet50 saved to {RESNET_PATH}")
else:
    print(f"  ResNet50 already present at {RESNET_PATH}")

marker = os.path.join(DISTILBERT_DIR, "model.safetensors")
if not os.path.exists(marker):
    print("Downloading DistilBERT (255MB)...")
    models_dir = os.path.dirname(DISTILBERT_DIR)
    os.makedirs(models_dir, exist_ok=True)
    snapshot_download(
        "nehagdd/rescue-ai-models",
        allow_patterns="distilbert/*",
        local_dir=models_dir,
    )
    dl = os.path.join(models_dir, "distilbert")
    if os.path.isdir(dl) and not os.path.isdir(DISTILBERT_DIR):
        shutil.move(dl, DISTILBERT_DIR)
    print(f"  DistilBERT saved to {DISTILBERT_DIR}")
else:
    print(f"  DistilBERT already present at {DISTILBERT_DIR}")

print("All models ready!")
