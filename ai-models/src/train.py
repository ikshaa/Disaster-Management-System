# train.py
# Purpose: Train ResNet50 on AIDER disaster dataset
# Run:     python ai-models/src/train.py

import os
import time
import numpy as np
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
import torchvision.models as models
from torch.optim import Adam
from torch.optim.lr_scheduler import ReduceLROnPlateau
from tqdm import tqdm

# Import our dataset pipeline
from dataset import (get_dataloaders, IDX_TO_CLASS,
                     CLASS_TO_IDX, SEVERITY)

# ── Config ──────────────────────────────────────────────
DATASET_PATH  = "ai-models/data/raw/AIDER"
OUTPUT_PATH   = "ai-models/outputs"
CHECKPOINT    = "ai-models/outputs/best_model.pt"

NUM_CLASSES   = 5
BATCH_SIZE    = 32
NUM_EPOCHS    = 20
LEARNING_RATE = 0.0001   # small LR for fine tuning pretrained model

os.makedirs(OUTPUT_PATH, exist_ok=True)

# ── Device Setup ─────────────────────────────────────────
# This is specific to your M1 Pro Mac
def get_device():
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        print("  Using: Apple M1 Pro GPU (MPS) ✅")
    elif torch.cuda.is_available():
        device = torch.device("cuda")
        print("  Using: NVIDIA GPU (CUDA) ✅")
    else:
        device = torch.device("cpu")
        print("  Using: CPU ⚠️  (training will be slow)")
    return device

# ── Model Setup ──────────────────────────────────────────
def build_model(num_classes, device):
    """
    Load pretrained ResNet50 and modify for our task.

    ResNet50 architecture:
    Input(224x224x3)
      → Conv layers (learn edges, textures)
      → Layer1, Layer2, Layer3 (learn shapes, patterns)
      → Layer4 (learn high level features)
      → AdaptiveAvgPool
      → FC layer (1000 classes) ← we REPLACE this
      → Our FC layer (5 classes) ← with this
    """
    # Load ResNet50 with ImageNet pretrained weights
    model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
    print("  Loaded ResNet50 with ImageNet pretrained weights ✅")

    # ── Freeze early layers ──────────────────────────────
    # These detect basic features (edges, colors, gradients)
    # Already perfect from ImageNet training
    # No need to retrain → saves time + prevents overfitting
    for name, param in model.named_parameters():
        if 'layer4' not in name and 'fc' not in name:
            param.requires_grad = False
        # layer4 and fc remain trainable
        # layer4 learns high-level disaster-specific features
        # fc is our new classification head

    # Count trainable vs frozen parameters
    trainable = sum(p.numel() for p in model.parameters()
                    if p.requires_grad)
    total     = sum(p.numel() for p in model.parameters())
    print(f"  Trainable parameters: {trainable:,} / {total:,} "
          f"({100*trainable/total:.1f}%)")

    # ── Replace final layer ──────────────────────────────
    # Original ResNet50 fc: 2048 → 1000 (ImageNet classes)
    # Our fc:               2048 → 5    (disaster classes)
    in_features = model.fc.in_features   # 2048
    model.fc = nn.Sequential(
        nn.Dropout(p=0.3),          # dropout prevents overfitting
        nn.Linear(in_features, 256),
        nn.ReLU(),
        nn.Dropout(p=0.2),
        nn.Linear(256, num_classes)  # final output: 5 classes
    )
    print(f"  Replaced FC layer: 2048 → 256 → {num_classes} ✅")

    model = model.to(device)
    return model

# ── Loss Function with Class Weights ─────────────────────
def get_loss_function(train_samples, device):
    """
    CrossEntropyLoss with class weights.
    Rare classes (fire, flood) get higher penalty when wrong.
    Normal class gets lower penalty.
    These weights came from our dataset.py output.
    """
    from collections import Counter
    labels       = [s[1] for s in train_samples]
    class_counts = Counter(labels)
    total        = len(labels)

    # weight = total / (num_classes * class_count)
    weights = []
    for idx in range(NUM_CLASSES):
        count  = class_counts[idx]
        weight = total / (NUM_CLASSES * count)
        weights.append(weight)

    weight_tensor = torch.tensor(weights, dtype=torch.float32).to(device)
    print(f"\n  Class weights applied to loss:")
    for idx, w in enumerate(weights):
        print(f"    {IDX_TO_CLASS[idx]:<25} {w:.3f}")

    return nn.CrossEntropyLoss(weight=weight_tensor)

# ── Training Loop ────────────────────────────────────────
def train_one_epoch(model, loader, criterion, optimizer, device):
    """
    One full pass through training data.
    Updates model weights after each batch.
    Returns average loss and accuracy for the epoch.
    """
    model.train()   # tells model we are training
                    # activates dropout, batch norm in train mode

    total_loss = 0.0
    correct    = 0
    total      = 0

    for images, labels in tqdm(loader, desc="  Training",
                                leave=False):
        # Move data to GPU (MPS)
        images = images.to(device)
        labels = labels.to(device)

        # 1. Forward pass — get predictions
        outputs = model(images)
        # outputs shape: [32, 5] — 5 scores per image

        # 2. Compute loss — how wrong are we?
        loss = criterion(outputs, labels)

        # 3. Backward pass — compute gradients
        optimizer.zero_grad()   # clear previous gradients
        loss.backward()         # compute new gradients

        # 4. Update weights
        optimizer.step()

        # Track metrics
        total_loss += loss.item()
        _, predicted = outputs.max(1)   # class with highest score
        correct += predicted.eq(labels).sum().item()
        total   += labels.size(0)

    avg_loss = total_loss / len(loader)
    accuracy = 100.0 * correct / total
    return avg_loss, accuracy

# ── Validation Loop ──────────────────────────────────────
def validate(model, loader, criterion, device):
    """
    One full pass through validation data.
    NO weight updates — just measuring performance.
    Returns average loss and accuracy.
    """
    model.eval()    # tells model we are evaluating
                    # deactivates dropout, batch norm in eval mode

    total_loss = 0.0
    correct    = 0
    total      = 0

    with torch.no_grad():   # don't compute gradients
                            # saves memory and speeds up validation
        for images, labels in tqdm(loader, desc="  Validating",
                                    leave=False):
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)
            loss    = criterion(outputs, labels)

            total_loss += loss.item()
            _, predicted = outputs.max(1)
            correct += predicted.eq(labels).sum().item()
            total   += labels.size(0)

    avg_loss = total_loss / len(loader)
    accuracy = 100.0 * correct / total
    return avg_loss, accuracy

# ── Plot Training Curves ──────────────────────────────────
def plot_curves(history):
    """
    Plots train vs val loss and accuracy over epochs.
    Visual way to detect overfitting.
    """
    epochs = range(1, len(history['train_loss']) + 1)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Loss curves
    ax1.plot(epochs, history['train_loss'],
             'b-o', label='Train Loss')
    ax1.plot(epochs, history['val_loss'],
             'r-o', label='Val Loss')
    ax1.set_title('Loss over Epochs')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss')
    ax1.legend()
    ax1.grid(True)

    # Accuracy curves
    ax2.plot(epochs, history['train_acc'],
             'b-o', label='Train Accuracy')
    ax2.plot(epochs, history['val_acc'],
             'r-o', label='Val Accuracy')
    ax2.set_title('Accuracy over Epochs')
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Accuracy %')
    ax2.legend()
    ax2.grid(True)

    plt.suptitle('AIDER Training — ResNet50 Fine Tuning', fontsize=13)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_PATH}/training_curves.png")
    print(f"  Saved → {OUTPUT_PATH}/training_curves.png")

# ── Main Training Function ────────────────────────────────
def train():
    print("\n" + "="*50)
    print("  AIDER Disaster Classification Training")
    print("  Model: ResNet50 (Transfer Learning)")
    print("="*50)

    # Step 1: Device
    print("\n[1/6] Setting up device...")
    device = get_device()

    # Step 2: Data
    print("\n[2/6] Loading data...")
    train_loader, val_loader, test_loader, train_samples = \
        get_dataloaders(DATASET_PATH, BATCH_SIZE)

    # Step 3: Model
    print("\n[3/6] Building model...")
    model = build_model(NUM_CLASSES, device)

    # Step 4: Loss + Optimizer
    print("\n[4/6] Setting up loss and optimizer...")
    criterion = get_loss_function(train_samples, device)
    optimizer = Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=LEARNING_RATE,
        weight_decay=1e-4   # L2 regularization, helps prevent overfitting
    )

    # Reduce learning rate when val loss stops improving
    # patience=3 means wait 3 epochs before reducing
    scheduler = ReduceLROnPlateau(
        optimizer,
        mode='min',         # minimize val loss
        patience=3,
        factor=0.5,         # multiply LR by 0.5
    )

    # Step 5: Training loop
    print("\n[5/6] Training...\n")
    history = {
        'train_loss': [], 'val_loss': [],
        'train_acc':  [], 'val_acc':  []
    }

    best_val_acc  = 0.0
    best_epoch    = 0
    no_improve    = 0
    EARLY_STOP    = 7   # stop if no improvement for 7 epochs

    for epoch in range(1, NUM_EPOCHS + 1):
        start = time.time()

        # Train
        train_loss, train_acc = train_one_epoch(
            model, train_loader, criterion, optimizer, device)

        # Validate
        val_loss, val_acc = validate(
            model, val_loader, criterion, device)

        # Update scheduler
        scheduler.step(val_loss)

        # Track history
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['train_acc'].append(train_acc)
        history['val_acc'].append(val_acc)

        elapsed = time.time() - start

        # Print epoch summary
        print(f"  Epoch [{epoch:02d}/{NUM_EPOCHS}] "
              f"| Time: {elapsed:.1f}s "
              f"| Train Loss: {train_loss:.4f} "
              f"| Train Acc: {train_acc:.1f}% "
              f"| Val Loss: {val_loss:.4f} "
              f"| Val Acc: {val_acc:.1f}%",
              end="")

        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_epoch   = epoch
            no_improve   = 0
            torch.save({
                'epoch':      epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_acc':    val_acc,
                'val_loss':   val_loss,
                'class_to_idx': CLASS_TO_IDX,
            }, CHECKPOINT)
            print(f" ← best saved ✅")
        else:
            no_improve += 1
            print(f" (no improve {no_improve}/{EARLY_STOP})")

        # Early stopping
        if no_improve >= EARLY_STOP:
            print(f"\n  Early stopping at epoch {epoch}")
            print(f"  Best was epoch {best_epoch} "
                  f"with val_acc={best_val_acc:.1f}%")
            break

    # Step 6: Final summary
    print(f"\n[6/6] Training complete!")
    print(f"  Best epoch:    {best_epoch}")
    print(f"  Best val acc:  {best_val_acc:.1f}%")
    print(f"  Model saved:   {CHECKPOINT}")

    plot_curves(history)
    print("\n  Next step → evaluate.py")
    return model, test_loader, device

# ── Entry Point ───────────────────────────────────────────
if __name__ == "__main__":
    model, test_loader, device = train()