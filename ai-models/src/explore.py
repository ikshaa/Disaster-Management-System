# explore.py
# Purpose: Understand our dataset before touching any model
# Run: python ai-models/src/explore.py

import os
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import cv2
from collections import defaultdict

# ── Config ──────────────────────────────────────────────
DATASET_PATH = "ai-models/data/raw/AIDER"
OUTPUT_PATH  = "ai-models/outputs"
os.makedirs(OUTPUT_PATH, exist_ok=True)

# These are YOUR exact folder names
CLASSES = [
    'fire',
    'flooded_areas',
    'collapsed_building',
    'traffic_incident',
    'normal'
]

# ── Step 1: Count images per class ──────────────────────
print("\n=== STEP 1: Class Distribution ===")
class_counts = {}
for cls in CLASSES:
    path = os.path.join(DATASET_PATH, cls)
    images = [f for f in os.listdir(path)
              if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    class_counts[cls] = len(images)
    print(f"  {cls:<25} {len(images)} images")

total = sum(class_counts.values())
print(f"\n  Total images: {total}")

# ── Step 2: Plot class distribution ─────────────────────
print("\n=== STEP 2: Saving class distribution chart ===")
plt.figure(figsize=(10, 5))
bars = plt.bar(class_counts.keys(),
               class_counts.values(),
               color=['red','blue','brown','orange','green'])
plt.title("AIDER Dataset - Images per Class", fontsize=14)
plt.xlabel("Class")
plt.ylabel("Number of Images")
for bar, count in zip(bars, class_counts.values()):
    plt.text(bar.get_x() + bar.get_width()/2,
             bar.get_height() + 30,
             str(count), ha='center', fontsize=11)
plt.tight_layout()
plt.savefig(f"{OUTPUT_PATH}/class_distribution.png")
print(f"  Saved → {OUTPUT_PATH}/class_distribution.png")

# ── Step 3: Check image sizes ────────────────────────────
print("\n=== STEP 3: Checking image sizes ===")
size_info = defaultdict(list)
corrupted  = []

for cls in CLASSES:
    folder = os.path.join(DATASET_PATH, cls)
    files  = [f for f in os.listdir(folder)
              if f.lower().endswith(('.jpg','.jpeg','.png'))][:50]  # check 50 per class
    for fname in files:
        fpath = os.path.join(folder, fname)
        try:
            img = Image.open(fpath).convert('RGB')
            size_info[cls].append(img.size)  # (width, height)
        except Exception as e:
            corrupted.append(fpath)
            print(f"  CORRUPTED: {fpath}")

for cls in CLASSES:
    sizes  = size_info[cls]
    widths  = [s[0] for s in sizes]
    heights = [s[1] for s in sizes]
    print(f"  {cls:<25} "
          f"W: {min(widths)}–{max(widths)}  "
          f"H: {min(heights)}–{max(heights)}")

print(f"\n  Corrupted files found: {len(corrupted)}")

# ── Step 4: Visual sample grid ───────────────────────────
print("\n=== STEP 4: Saving sample image grid ===")
fig, axes = plt.subplots(len(CLASSES), 4, figsize=(16, 20))

for i, cls in enumerate(CLASSES):
    folder = os.path.join(DATASET_PATH, cls)
    files  = [f for f in os.listdir(folder)
              if f.lower().endswith(('.jpg','.jpeg','.png'))][:4]
    for j, fname in enumerate(files):
        fpath = os.path.join(folder, fname)
        try:
            img = Image.open(fpath).convert('RGB')
            axes[i][j].imshow(img)
            axes[i][j].set_title(f"{cls}\n{img.size[0]}×{img.size[1]}",
                                  fontsize=8)
        except:
            axes[i][j].set_title("CORRUPTED", color='red')
        axes[i][j].axis('off')

plt.suptitle("AIDER Dataset — Sample Images per Class", fontsize=14)
plt.tight_layout()
plt.savefig(f"{OUTPUT_PATH}/sample_grid.png")
print(f"  Saved → {OUTPUT_PATH}/sample_grid.png")

# ── Step 5: Summary ──────────────────────────────────────
print("\n=== STEP 5: Summary ===")
minority_avg = np.mean([v for k,v in class_counts.items() if k != 'normal'])
print(f"  Imbalance ratio: {class_counts['normal']/minority_avg:.1f}x "
      f"(normal vs average minority)")
print(f"  Smallest class:  "
      f"{min(class_counts, key=class_counts.get)} "
      f"({min(class_counts.values())} images)")
print(f"  Action needed:   WeightedSampler + Class weights in loss ✅")
print("\n  EDA Complete. Check ai-models/outputs/ for charts.")
