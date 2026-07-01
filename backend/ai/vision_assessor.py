import os
import logging
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(__file__)
CHECKPOINT_PATH = os.path.abspath(os.path.join(BASE_DIR, "../../ai-models/outputs/best_model.pt"))

NUM_CLASSES = 5
IDX_TO_CLASS = {
    0: "fire",
    1: "flooded_areas",
    2: "collapsed_building",
    3: "traffic_incident",
    4: "normal",
}

IMAGE_BASE_SCORES = {
    "collapsed_building": 9.0,
    "fire": 8.0,
    "flooded_areas": 6.0,
    "traffic_incident": 4.0,
    "normal": 0.0,
}

SEVERITY_MAP = {
    "collapsed_building": "CRITICAL",
    "fire": "CRITICAL",
    "flooded_areas": "HIGH",
    "traffic_incident": "MEDIUM",
    "normal": "LOW",
}

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

_vision_model = None
_device = None


def _load_model():
    global _vision_model, _device
    if _vision_model is None:
        if not os.path.exists(CHECKPOINT_PATH):
            raise FileNotFoundError(f"ResNet50 checkpoint not found at {CHECKPOINT_PATH}")
        import torch
        import torch.nn as nn
        from torchvision import models

        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        model = models.resnet50(weights=None)
        in_features = model.fc.in_features
        model.fc = nn.Sequential(
            nn.Dropout(p=0.3),
            nn.Linear(in_features, 256),
            nn.ReLU(),
            nn.Dropout(p=0.2),
            nn.Linear(256, NUM_CLASSES),
        )

        checkpoint = torch.load(CHECKPOINT_PATH, map_location=_device, weights_only=True)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(_device)
        model.eval()
        _vision_model = model
        logger.info("ResNet50 vision model loaded")
    return _vision_model, _device


def _preprocess(image_path: str):
    import torch
    img = Image.open(image_path).convert("RGB")
    img = img.resize((224, 224), Image.LANCZOS)
    arr = np.array(img, dtype=np.float32) / 255.0
    arr = (arr - IMAGENET_MEAN) / IMAGENET_STD
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)
    return tensor


def analyze_image(image_path: str) -> dict:
    try:
        model, device = _load_model()
        import torch
        tensor = _preprocess(image_path).to(device)

        with torch.no_grad():
            logits = model(tensor)[0]
            probs = torch.softmax(logits, dim=0).cpu().numpy()

        pred_idx = int(np.argmax(probs))
        pred_class = IDX_TO_CLASS[pred_idx]
        confidence = round(float(probs[pred_idx]), 4)

        base_score = IMAGE_BASE_SCORES.get(pred_class, 0.0)
        image_score = round(base_score * confidence, 1)

        return {
            "image_class": pred_class,
            "severity": SEVERITY_MAP.get(pred_class, "LOW"),
            "confidence": confidence,
            "image_score": image_score,
            "all_probs": {IDX_TO_CLASS[i]: round(float(probs[i]), 4) for i in range(NUM_CLASSES)},
        }
    except Exception as e:
        logger.error(f"Vision analysis failed: {e}")
        return {
            "image_class": "unknown",
            "severity": "UNKNOWN",
            "confidence": 0.0,
            "image_score": 0.0,
            "all_probs": {},
        }
