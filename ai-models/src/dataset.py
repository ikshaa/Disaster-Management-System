# dataset.py
# Purpose: PyTorch Dataset class that connects preprocessing
#          and augmentation into one pipeline PyTorch can use
# Run:     python ai-models/src/dataset.py

import os
import numpy as np
from PIL import Image
import torch
from torch.utils.data import (Dataset, DataLoader,
                               WeightedRandomSampler)
from sklearn.model_selection import train_test_split
from collections import Counter
import matplotlib.pyplot as plt
import albumentations as A
from albumentations.pytorch import ToTensorV2

# ── Config ──────────────────────────────────────────────
DATASET_PATH = "ai-models/data/raw/AIDER"
OUTPUT_PATH  = "ai-models/outputs"
RANDOM_SEED  = 42       # fixed seed = reproducible splits every time
BATCH_SIZE   = 32       # 32 images per batch, standard for M1 Pro
NUM_WORKERS  = 0        # 0 = main process only (safest for Mac/MPS)

# Map class folder names to numbers
# Model outputs numbers, we map back to names for display
CLASS_TO_IDX = {
    'fire':                0,
    'flooded_areas':       1,
    'collapsed_building':  2,
    'traffic_incident':    3,
    'normal':              4
}
IDX_TO_CLASS = {v: k for k, v in CLASS_TO_IDX.items()}

# Severity mapping — connects to your priority scoring system
# This is where image model output feeds firefighter dispatch
SEVERITY = {
    'fire':                'CRITICAL',
    'flooded_areas':       'HIGH',
    'collapsed_building':  'CRITICAL',
    'traffic_incident':    'MEDIUM',
    'normal':              'LOW'
}

# ── Transforms ──────────────────────────────────────────
# Training: random augmentations + normalize + tensor
train_transform = A.Compose([
    A.Resize(224, 224),
    A.HorizontalFlip(p=0.5),
    A.Rotate(limit=15, p=0.5),
    A.RandomResizedCrop(size=(224, 224), scale=(0.8, 1.0), p=0.3),
    A.Affine(
        translate_percent=0.1,
        scale=(0.9, 1.1),
        rotate=(-10, 10),
        p=0.4
    ),
    A.RandomBrightnessContrast(p=0.5),
    A.HueSaturationValue(p=0.3),
    A.GaussianBlur(blur_limit=3, p=0.2),
    A.RandomShadow(p=0.3),
    A.RandomFog(fog_coef_range=(0.1, 0.3), p=0.2),
    A.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    ),
    ToTensorV2()
])

# Validation/Test: only resize + normalize, no randomness
val_transform = A.Compose([
    A.Resize(224, 224),
    A.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    ),
    ToTensorV2()
])

# ── Dataset Class ────────────────────────────────────────
class AIDERDataset(Dataset):
    """
    Custom PyTorch Dataset for AIDER aerial disaster images.

    Usage:
        dataset = AIDERDataset(samples, transform=train_transform)
        image, label = dataset[0]
    """

    def __init__(self, samples, transform=None):
        """
        samples   → list of (image_path, label_int) tuples
        transform → albumentations pipeline to apply
        """
        self.samples   = samples
        self.transform = transform

    def __len__(self):
        # PyTorch calls this to know total dataset size
        return len(self.samples)

    def __getitem__(self, idx):
        """
        PyTorch calls this with an index during training
        Returns: (tensor of shape [3,224,224], integer label)
        """
        img_path, label = self.samples[idx]

        # Load image — always convert to RGB
        img = np.array(
            Image.open(img_path).convert('RGB')
        )

        # Apply transform (train or val pipeline)
        if self.transform:
            img = self.transform(image=img)['image']

        # label must be a tensor for PyTorch loss function
        return img, torch.tensor(label, dtype=torch.long)


# ── Build Sample List ────────────────────────────────────
def build_samples(dataset_path, class_to_idx):
    """
    Walks through AIDER folders and builds a flat list:
    [
        ('path/to/fire/img1.jpg', 0),
        ('path/to/fire/img2.jpg', 0),
        ('path/to/flooded/img1.jpg', 1),
        ...
    ]
    """
    samples = []
    for class_name, label in class_to_idx.items():
        folder = os.path.join(dataset_path, class_name)
        for fname in os.listdir(folder):
            if fname.lower().endswith(('.jpg','.jpeg','.png')):
                samples.append((
                    os.path.join(folder, fname),
                    label
                ))
    return samples


# ── Train / Val / Test Split ─────────────────────────────
def split_samples(samples, seed=RANDOM_SEED):
    """
    Splits samples into 70% train, 15% val, 15% test.
    Uses stratify to maintain class ratios in all splits.
    """
    labels = [s[1] for s in samples]

    # First split: 70% train, 30% temp
    train, temp, _, temp_labels = train_test_split(
        samples, labels,
        test_size=0.30,
        stratify=labels,        # preserve class ratios
        random_state=seed
    )

    # Second split: 50% of temp = 15% val, 15% test
    val, test = train_test_split(
        temp,
        test_size=0.50,
        stratify=temp_labels,   # preserve class ratios
        random_state=seed
    )

    return train, val, test


# ── WeightedRandomSampler ────────────────────────────────
def make_weighted_sampler(train_samples):
    """
    Gives rare classes higher sampling probability.
    So model sees roughly equal classes per epoch
    despite 8.6x imbalance in raw data.
    """
    labels = [s[1] for s in train_samples]

    # Count images per class
    class_counts = Counter(labels)

    # Weight = inverse of count
    # rare class (485 images)  → high weight
    # common class (4390 images) → low weight
    class_weights = {
        cls: 1.0 / count
        for cls, count in class_counts.items()
    }

    # Assign weight to every single sample
    sample_weights = [
        class_weights[label] for label in labels
    ]

    sampler = WeightedRandomSampler(
        weights=sample_weights,
        num_samples=len(sample_weights),
        replacement=True    # allows same image to appear
                            # multiple times per epoch
                            # needed for oversampling minority
    )
    return sampler


# ── Create DataLoaders ───────────────────────────────────
def get_dataloaders(dataset_path, batch_size=BATCH_SIZE):
    """
    Master function — call this from train.py
    Returns three DataLoaders ready to use.
    """
    # Step 1: build flat list of all (path, label) pairs
    all_samples = build_samples(dataset_path, CLASS_TO_IDX)
    print(f"  Total samples found: {len(all_samples)}")

    # Step 2: split into train/val/test
    train_samples, val_samples, test_samples = split_samples(all_samples)
    print(f"  Train: {len(train_samples)} | "
          f"Val: {len(val_samples)} | "
          f"Test: {len(test_samples)}")

    # Step 3: create Dataset objects
    train_dataset = AIDERDataset(train_samples, transform=train_transform)
    val_dataset   = AIDERDataset(val_samples,   transform=val_transform)
    test_dataset  = AIDERDataset(test_samples,  transform=val_transform)
    # note: test uses val_transform (no augmentation)

    # Step 4: create weighted sampler for training only
    sampler = make_weighted_sampler(train_samples)

    # Step 5: wrap in DataLoaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        sampler=sampler,        # weighted sampling
        num_workers=NUM_WORKERS,
        pin_memory=False        # False for MPS (Apple GPU)
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,          # no shuffling for val/test
        num_workers=NUM_WORKERS,
        pin_memory=False
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=NUM_WORKERS,
        pin_memory=False
    )

    return train_loader, val_loader, test_loader, train_samples


# ── Verify a Batch ───────────────────────────────────────
def verify_batch(loader, split_name):
    """
    Fetches one batch and prints its properties.
    Sanity check before training.
    """
    images, labels = next(iter(loader))
    print(f"\n  {split_name} batch:")
    print(f"    images shape: {images.shape}")
    # Expected: torch.Size([32, 3, 224, 224])
    # 32=batch, 3=RGB channels, 224x224=size

    print(f"    labels shape: {labels.shape}")
    # Expected: torch.Size([32])

    print(f"    image dtype:  {images.dtype}")
    # Expected: torch.float32

    print(f"    pixel range:  "
          f"{images.min():.2f} to {images.max():.2f}")
    # Expected: roughly -2.0 to 2.5 (ImageNet normalized)

    # Show class distribution in this batch
    class_dist = Counter(labels.numpy())
    print(f"    class distribution in batch:")
    for idx, count in sorted(class_dist.items()):
        print(f"      {IDX_TO_CLASS[idx]:<25} {count} images")


# ── Visualize Batch ──────────────────────────────────────
def visualize_batch(loader):
    """
    Shows first 10 images from a training batch.
    De-normalizes for display.
    """
    images, labels = next(iter(loader))

    # Reverse ImageNet normalization for display
    mean = torch.tensor([0.485, 0.456, 0.406]).view(3,1,1)
    std  = torch.tensor([0.229, 0.224, 0.225]).view(3,1,1)

    fig, axes = plt.subplots(2, 5, figsize=(15, 6))
    for i, ax in enumerate(axes.flat):
        img = images[i]
        img = img * std + mean          # de-normalize
        img = img.permute(1, 2, 0)      # (C,H,W) → (H,W,C)
        img = img.numpy().clip(0, 1)    # clip to valid range

        ax.imshow(img)
        ax.set_title(IDX_TO_CLASS[labels[i].item()], fontsize=8)
        ax.axis('off')

    plt.suptitle("Sample Training Batch (after augmentation)", fontsize=12)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_PATH}/sample_batch.png")
    print(f"\n  Saved → {OUTPUT_PATH}/sample_batch.png")


# ── Main ─────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n=== Building AIDER DataLoaders ===")

    train_loader, val_loader, test_loader, train_samples = \
        get_dataloaders(DATASET_PATH)

    print("\n=== Verifying Batches ===")
    verify_batch(train_loader, "TRAIN")
    verify_batch(val_loader,   "VAL")
    verify_batch(test_loader,  "TEST")

    print("\n=== Saving Sample Batch Visualization ===")
    visualize_batch(train_loader)

    print("\n=== Class Weights for Loss Function ===")
    # Compute class weights for CrossEntropyLoss
    # This is the second line of defense against imbalance
    # (first was WeightedSampler)
    labels      = [s[1] for s in train_samples]
    class_counts = Counter(labels)
    total        = len(labels)
    print("  These go into your loss function in train.py:")
    for idx in range(len(CLASS_TO_IDX)):
        cls    = IDX_TO_CLASS[idx]
        count  = class_counts[idx]
        weight = total / (len(CLASS_TO_IDX) * count)
        print(f"  {cls:<25} count={count:<5} weight={weight:.3f}")

    print("\n  dataset.py complete ✅")
    print("  Next step → train.py")