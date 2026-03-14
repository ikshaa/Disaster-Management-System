# augmentation.py
# Purpose: Define augmentation pipelines for training
# Visualize what augmented images look like
# Run: python ai-models/src/augmentation.py

import os
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import albumentations as A
from albumentations.pytorch import ToTensorV2

# ── Config ──────────────────────────────────────────────
DATASET_PATH  = "ai-models/data/raw/AIDER"
OUTPUT_VISUAL = "ai-models/outputs"

# ── Training Augmentation Pipeline ──────────────────────
# These are RANDOM transforms applied during training only
# Every time the model sees an image it looks slightly different
train_transform = A.Compose([
    A.Resize(224, 224),

    # --- Geometric transforms ---
    # Horizontal flip: aerial view looks same mirrored
    A.HorizontalFlip(p=0.5),

    # Small rotations: drone can be slightly tilted
    A.Rotate(limit=15, p=0.5),

    # Zoom/crop: simulates different drone altitudes
    A.RandomResizedCrop(
        size=(224, 224),
        scale=(0.8, 1.0),
        p=0.3
    ),

    # Shift/scale: disaster not always perfectly centered
    A.Affine(
        translate_percent=0.1,
        scale=(0.9, 1.1),
        rotate=(-10, 10),
        p=0.4
    ),

    # --- Photometric transforms ---
    # Brightness/contrast: time of day, weather
    A.RandomBrightnessContrast(
        brightness_limit=0.3,
        contrast_limit=0.3,
        p=0.5
    ),

    # Color shifting: different camera sensors
    A.HueSaturationValue(
        hue_shift_limit=20,
        sat_shift_limit=30,
        val_shift_limit=20,
        p=0.3
    ),

    # Blur: camera focus issues, distance
    A.GaussianBlur(blur_limit=3, p=0.2),

    # Shadow: clouds passing over disaster area
    A.RandomShadow(p=0.3),

    # Fog: realistic for disaster scenarios
    A.RandomFog(fog_coef_range=(0.1, 0.3), p=0.2),

    # --- Final normalization ---
    A.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    ),
    ToTensorV2()
])

# ── Validation/Test Pipeline ─────────────────────────────
# NO random transforms — only resize and normalize
# Must reflect real world exactly
val_transform = A.Compose([
    A.Resize(224, 224),
    A.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    ),
    ToTensorV2()
])

# ── Visualization Pipeline ───────────────────────────────
# Same as train but WITHOUT ToTensorV2 and Normalize
# So we can display the images as normal pictures
viz_transform = A.Compose([
    A.Resize(224, 224),
    A.HorizontalFlip(p=0.5),
    A.Rotate(limit=15, p=0.5),
    A.RandomResizedCrop(size=(224, 224), scale=(0.8, 1.0), p=0.3),
    A.RandomBrightnessContrast(p=0.5),
    A.HueSaturationValue(p=0.3),
    A.GaussianBlur(blur_limit=3, p=0.2),
    A.RandomShadow(p=0.3),
    A.RandomFog(fog_coef_range=(0.1, 0.3), p=0.2),
])

# ── Visualize augmentations on real images ───────────────
print("\n=== Visualizing Augmentations ===")
print("  Showing 6 augmented versions of same image per class")

fig, axes = plt.subplots(5, 6, figsize=(18, 15))

CLASSES = [
    'fire',
    'flooded_areas',
    'collapsed_building',
    'traffic_incident',
    'normal'
]

for i, cls in enumerate(CLASSES):
    folder = os.path.join(DATASET_PATH, cls)
    fname  = os.listdir(folder)[0]
    fpath  = os.path.join(folder, fname)

    # Load original
    img = np.array(Image.open(fpath).convert('RGB'))

    # Show original in first column
    resized = A.Resize(224, 224)(image=img)['image']
    axes[i][0].imshow(resized)
    axes[i][0].set_title(f"{cls}\nORIGINAL", fontsize=7)
    axes[i][0].axis('off')

    # Show 5 different augmented versions
    for j in range(1, 6):
        augmented = viz_transform(image=img)['image']
        axes[i][j].imshow(augmented)
        axes[i][j].set_title(f"Aug #{j}", fontsize=7)
        axes[i][j].axis('off')

plt.suptitle(
    "Augmentation Pipeline — Same Image, Different Random Transforms",
    fontsize=13
)
plt.tight_layout()
save_path = f"{OUTPUT_VISUAL}/augmentation_preview.png"
plt.savefig(save_path)
print(f"  Saved → {save_path}")

# ── Print pipeline summary ───────────────────────────────
print("\n=== Augmentation Pipeline Summary ===")
print("""
  TRAIN pipeline:
    Resize 224×224          → standardize size
    HorizontalFlip (p=0.5)  → mirror image
    Rotate ±15° (p=0.5)     → drone tilt
    RandomResizedCrop (p=0.3) → altitude simulation
    ShiftScaleRotate (p=0.4)  → position variation
    BrightnessContrast (p=0.5)→ lighting conditions
    HueSaturation (p=0.3)   → camera differences
    GaussianBlur (p=0.2)    → focus variation
    RandomShadow (p=0.3)    → cloud shadows
    RandomFog (p=0.2)       → weather conditions
    Normalize (ImageNet)    → match pretrained model
    ToTensorV2              → convert to PyTorch tensor

  VAL/TEST pipeline:
    Resize 224×224          → standardize only
    Normalize (ImageNet)    → match pretrained model
    ToTensorV2              → convert to PyTorch tensor

  Rule: Augmentation on TRAIN only. Never val/test.
""")
print("  augmentation.py complete ✅")
print("  Next step → dataset.py")