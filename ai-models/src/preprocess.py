# preprocess.py
# Purpose: Resize, normalize and verify all AIDER images
# Run from project root: python ai-models/src/preprocess.py

import os
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import cv2
from tqdm import tqdm

# ── Config ──────────────────────────────────────────────
DATASET_PATH  = "ai-models/data/raw/AIDER"
OUTPUT_PATH   = "ai-models/data/processed"
OUTPUT_VISUAL = "ai-models/outputs"
TARGET_SIZE   = (224, 224)

# YOUR exact folder names from EDA
CLASSES = [
    'fire',
    'flooded_areas',
    'collapsed_building',
    'traffic_incident',
    'normal'
]

# ImageNet stats — required because we use pretrained models
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406])
IMAGENET_STD  = np.array([0.229, 0.224, 0.225])

os.makedirs(OUTPUT_VISUAL, exist_ok=True)

# ── Step 1: Single image preprocessor ───────────────────
def preprocess_image(img_path):
    """
    Takes a raw image path.
    Returns a normalized numpy array of shape (224, 224, 3)
    Returns None if image is corrupted.
    """
    try:
        # Open and force RGB (handles RGBA, grayscale, CMYK)
        img = Image.open(img_path).convert('RGB')

        # Resize to 224x224
        # LANCZOS = best quality for downscaling large images
        img = img.resize(TARGET_SIZE, Image.LANCZOS)

        # Convert to numpy array → shape (224, 224, 3)
        img_array = np.array(img, dtype=np.float32)

        # Scale pixels from 0-255 → 0.0-1.0
        img_array = img_array / 255.0

        # Apply ImageNet normalization
        img_array = (img_array - IMAGENET_MEAN) / IMAGENET_STD

        return img_array

    except Exception as e:
        print(f"  ERROR processing {img_path}: {e}")
        return None

# ── Step 2: Verify preprocessing works on one image ─────
print("\n=== STEP 1: Testing on single image ===")
test_class = 'fire'
test_folder = os.path.join(DATASET_PATH, test_class)
test_image  = os.listdir(test_folder)[0]
test_path   = os.path.join(test_folder, test_image)

# Before preprocessing
original = Image.open(test_path).convert('RGB')
print(f"  Original size:  {original.size}")
print(f"  Original mode:  {original.mode}")

# After preprocessing
processed = preprocess_image(test_path)
print(f"  Processed shape: {processed.shape}")
print(f"  Pixel min: {processed.min():.3f}")
print(f"  Pixel max: {processed.max():.3f}")
print(f"  Pixel mean: {processed.mean():.3f}")
# After ImageNet normalization values will be roughly -2 to +2
# This is expected and correct

# ── Step 3: Visualize before vs after ───────────────────
print("\n=== STEP 2: Saving before/after comparison ===")

fig, axes = plt.subplots(2, 5, figsize=(20, 8))

for i, cls in enumerate(CLASSES):
    folder = os.path.join(DATASET_PATH, cls)
    fname  = os.listdir(folder)[0]
    fpath  = os.path.join(folder, fname)

    # Original image (top row)
    orig = Image.open(fpath).convert('RGB')
    axes[0][i].imshow(orig)
    axes[0][i].set_title(f"ORIGINAL\n{cls}\n{orig.size[0]}×{orig.size[1]}",
                          fontsize=8)
    axes[0][i].axis('off')

    # Processed image (bottom row)
    # De-normalize for display only (can't show normalized values as image)
    proc = preprocess_image(fpath)
    display = (proc * IMAGENET_STD + IMAGENET_MEAN)  # reverse normalization
    display = np.clip(display, 0, 1)                 # clip to valid range
    axes[1][i].imshow(display)
    axes[1][i].set_title(f"PROCESSED\n224×224", fontsize=8)
    axes[1][i].axis('off')

plt.suptitle("Preprocessing: Original vs Resized (224×224)", fontsize=13)
plt.tight_layout()
plt.savefig(f"{OUTPUT_VISUAL}/preprocessing_comparison.png")
print(f"  Saved → {OUTPUT_VISUAL}/preprocessing_comparison.png")

# ── Step 4: Run on full dataset and report ───────────────
print("\n=== STEP 3: Processing full dataset ===")
stats = {}

for cls in CLASSES:
    folder  = os.path.join(DATASET_PATH, cls)
    files   = [f for f in os.listdir(folder)
               if f.lower().endswith(('.jpg','.jpeg','.png'))]
    success = 0
    failed  = 0

    for fname in tqdm(files, desc=f"  {cls:<25}"):
        fpath  = os.path.join(folder, fname)
        result = preprocess_image(fpath)
        if result is not None:
            success += 1
        else:
            failed += 1

    stats[cls] = {'success': success, 'failed': failed}

# ── Step 5: Final report ─────────────────────────────────
print("\n=== STEP 4: Preprocessing Report ===")
total_success = 0
total_failed  = 0
for cls, s in stats.items():
    status = "✅" if s['failed'] == 0 else "⚠️"
    print(f"  {status} {cls:<25} "
          f"processed: {s['success']}  failed: {s['failed']}")
    total_success += s['success']
    total_failed  += s['failed']

print(f"\n  Total processed: {total_success}")
print(f"  Total failed:    {total_failed}")
print(f"\n  Target size:     {TARGET_SIZE}")
print(f"  Normalization:   ImageNet (mean/std)")
print(f"\n  preprocess.py complete ✅")
print(f"  Next step → augmentation.py")