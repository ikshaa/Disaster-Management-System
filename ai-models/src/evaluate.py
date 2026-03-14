# evaluate.py
# Purpose: Deep evaluation of trained model on test set
# Produces confusion matrix, per-class metrics, error analysis
# Run: python ai-models/src/evaluate.py

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import torch
import torch.nn as nn
import torchvision.models as models
from torch.utils.data import DataLoader
from sklearn.metrics import (
    confusion_matrix,
    classification_report,
    f1_score,
    precision_score,
    recall_score
)
import seaborn as sns
from tqdm import tqdm
from PIL import Image

# Import our pipeline
from dataset import (get_dataloaders, IDX_TO_CLASS,
                     CLASS_TO_IDX, SEVERITY, DATASET_PATH)

# ── Config ──────────────────────────────────────────────
OUTPUT_PATH = "ai-models/outputs"
CHECKPOINT  = "ai-models/outputs/best_model.pt"
NUM_CLASSES = 5
BATCH_SIZE  = 32

os.makedirs(OUTPUT_PATH, exist_ok=True)

# ── Device ───────────────────────────────────────────────
def get_device():
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")

# ── Load Trained Model ───────────────────────────────────
def load_model(checkpoint_path, device):
    """
    Rebuilds exact same architecture as train.py
    Loads saved weights from best checkpoint
    """
    # Rebuild architecture (must match train.py exactly)
    model = models.resnet50(weights=None)
    # weights=None because we load OUR weights, not ImageNet

    # Replace FC layer (must match train.py exactly)
    in_features = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(in_features, 256),
        nn.ReLU(),
        nn.Dropout(p=0.2),
        nn.Linear(256, NUM_CLASSES)
    )

    # Load saved weights
    checkpoint = torch.load(checkpoint_path,
                            map_location=device,
                            weights_only=True)
    model.load_state_dict(checkpoint['model_state_dict'])

    print(f"  Loaded checkpoint from epoch "
          f"{checkpoint['epoch']} "
          f"(val_acc={checkpoint['val_acc']:.1f}%)")

    model = model.to(device)
    model.eval()    # evaluation mode (no dropout, no gradient)
    return model

# ── Run Inference on Test Set ────────────────────────────
def get_predictions(model, test_loader, device):
    """
    Runs model on entire test set.
    Returns all true labels and predicted labels.
    """
    all_preds  = []
    all_labels = []
    all_probs  = []   # confidence scores

    with torch.no_grad():
        for images, labels in tqdm(test_loader,
                                    desc="  Running inference"):
            images = images.to(device)

            # Forward pass
            outputs = model(images)

            # Convert raw scores to probabilities
            probs = torch.softmax(outputs, dim=1)

            # Get predicted class (highest probability)
            _, predicted = outputs.max(1)

            all_preds.extend(predicted.cpu().numpy())
            all_labels.extend(labels.numpy())
            all_probs.extend(probs.cpu().numpy())

    return (np.array(all_labels),
            np.array(all_preds),
            np.array(all_probs))

# ── Confusion Matrix ─────────────────────────────────────
def plot_confusion_matrix(true_labels, pred_labels):
    """
    Visual grid showing what got confused with what.

    Perfect model: diagonal is all dark blue
                   everything else is white (zero)

    Problem areas: bright colors OFF the diagonal
                   e.g. fire predicted as normal
    """
    class_names = [IDX_TO_CLASS[i] for i in range(NUM_CLASSES)]
    cm = confusion_matrix(true_labels, pred_labels)

    # Normalize to percentages
    cm_percent = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
    cm_percent  = np.nan_to_num(cm_percent) * 100

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))

    # Raw counts
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=class_names,
                yticklabels=class_names, ax=ax1)
    ax1.set_title('Confusion Matrix (counts)', fontsize=13)
    ax1.set_ylabel('True Label')
    ax1.set_xlabel('Predicted Label')
    ax1.tick_params(axis='x', rotation=45)

    # Percentages
    sns.heatmap(cm_percent, annot=True, fmt='.1f', cmap='Blues',
                xticklabels=class_names,
                yticklabels=class_names, ax=ax2)
    ax2.set_title('Confusion Matrix (%)', fontsize=13)
    ax2.set_ylabel('True Label')
    ax2.set_xlabel('Predicted Label')
    ax2.tick_params(axis='x', rotation=45)

    plt.suptitle('AIDER Test Set — Confusion Matrix', fontsize=14)
    plt.tight_layout()
    path = f"{OUTPUT_PATH}/confusion_matrix.png"
    plt.savefig(path, bbox_inches='tight')
    print(f"  Saved → {path}")
    return cm, cm_percent

# ── Per Class Metrics ────────────────────────────────────
def print_detailed_metrics(true_labels, pred_labels):
    """
    Prints precision, recall, F1 per class.
    Highlights dangerous misses (low recall on disaster classes)
    """
    class_names = [IDX_TO_CLASS[i] for i in range(NUM_CLASSES)]

    print("\n  Per Class Metrics:")
    print(f"  {'Class':<25} {'Precision':>10} "
          f"{'Recall':>10} {'F1':>10} {'Support':>10}")
    print("  " + "─"*65)

    precisions = precision_score(true_labels, pred_labels,
                                  average=None)
    recalls    = recall_score(true_labels, pred_labels,
                               average=None)
    f1s        = f1_score(true_labels, pred_labels,
                           average=None)

    from collections import Counter
    support = Counter(true_labels)

    for i, cls in enumerate(class_names):
        severity = SEVERITY[cls]

        # Flag dangerous cases
        # Low recall on disaster class = missed emergencies
        flag = ""
        if recalls[i] < 0.85 and cls != 'normal':
            flag = " ⚠️  LOW RECALL"
        elif recalls[i] >= 0.95 and cls != 'normal':
            flag = " ✅"

        print(f"  {cls:<25} "
              f"{precisions[i]:>10.3f} "
              f"{recalls[i]:>10.3f} "
              f"{f1s[i]:>10.3f} "
              f"{support[i]:>10}"
              f"{flag}")

    print("  " + "─"*65)

    # Overall metrics
    print(f"\n  Overall Accuracy: "
          f"{100*np.mean(true_labels==pred_labels):.1f}%")
    print(f"  Macro F1:         "
          f"{f1_score(true_labels, pred_labels, average='macro'):.3f}")
    print(f"  Weighted F1:      "
          f"{f1_score(true_labels, pred_labels, average='weighted'):.3f}")

    return precisions, recalls, f1s

# ── Per Class Metrics Bar Chart ──────────────────────────
def plot_metrics_chart(precisions, recalls, f1s):
    """
    Bar chart comparing precision/recall/F1 per class.
    Easy to spot which class is weakest.
    """
    class_names = [IDX_TO_CLASS[i] for i in range(NUM_CLASSES)]
    x     = np.arange(len(class_names))
    width = 0.25

    fig, ax = plt.subplots(figsize=(13, 6))
    ax.bar(x - width, precisions, width, label='Precision',
           color='steelblue')
    ax.bar(x,         recalls,    width, label='Recall',
           color='coral')
    ax.bar(x + width, f1s,        width, label='F1 Score',
           color='mediumseagreen')

    ax.set_xticks(x)
    ax.set_xticklabels(class_names, rotation=15)
    ax.set_ylim(0, 1.1)
    ax.set_ylabel('Score')
    ax.set_title('Per Class: Precision / Recall / F1', fontsize=13)
    ax.legend()
    ax.axhline(y=0.85, color='red', linestyle='--',
               alpha=0.5, label='85% threshold')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    path = f"{OUTPUT_PATH}/per_class_metrics.png"
    plt.savefig(path)
    print(f"  Saved → {path}")

# ── Severity Priority Report ─────────────────────────────
def severity_report(true_labels, pred_labels, probs):
    """
    The most important output for your project.
    Shows how well the model supports firefighter dispatch.

    High severity classes MUST have high recall.
    Missing a CRITICAL event = failed emergency response.
    """
    print("\n" + "="*55)
    print("  DISASTER RESPONSE PRIORITY REPORT")
    print("="*55)
    print("  This is what matters for firefighter dispatch:\n")

    recalls = recall_score(true_labels, pred_labels, average=None)

    priority_order = [
        (2, 'collapsed_building', 'CRITICAL'),
        (0, 'fire',               'CRITICAL'),
        (1, 'flooded_areas',      'HIGH'),
        (3, 'traffic_incident',   'MEDIUM'),
        (4, 'normal',             'LOW'),
    ]

    for idx, cls, severity in priority_order:
        recall  = recalls[idx]
        bars    = int(recall * 20)
        bar_str = "█" * bars + "░" * (20 - bars)

        status = "✅ SAFE" if recall >= 0.90 else "⚠️  REVIEW"
        if recall < 0.80:
            status = "❌ DANGEROUS"

        print(f"  [{severity:<10}] {cls:<25}")
        print(f"             Recall: {bar_str} {recall*100:.1f}%"
              f"  {status}")
        print()

    print("  Recall = % of real disasters correctly detected")
    print("  Low recall = missed emergencies = dangerous")
    print("="*55)

# ── Confidence Analysis ──────────────────────────────────
def confidence_analysis(true_labels, pred_labels, probs):
    """
    Shows how confident the model is when correct vs wrong.
    Low confidence on correct predictions = model is uncertain
    High confidence on wrong predictions = model is overconfident
    """
    correct_mask   = (true_labels == pred_labels)
    correct_conf   = probs[correct_mask].max(axis=1).mean()
    incorrect_conf = probs[~correct_mask].max(axis=1).mean() \
                     if (~correct_mask).any() else 0

    print(f"\n  Confidence Analysis:")
    print(f"    Avg confidence when CORRECT:   "
          f"{correct_conf*100:.1f}%")
    print(f"    Avg confidence when WRONG:     "
          f"{incorrect_conf*100:.1f}%")

    if incorrect_conf > 0.7:
        print(f"    ⚠️  Model overconfident on errors")
    else:
        print(f"    ✅ Model appropriately uncertain on errors")

# ── Main ─────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*50)
    print("  AIDER Model Evaluation")
    print("  Test Set Analysis")
    print("="*50)

    # Step 1: Setup
    print("\n[1/6] Setting up...")
    device = get_device()
    print(f"  Device: {device}")

    # Step 2: Load data
    print("\n[2/6] Loading test data...")
    _, _, test_loader, _ = get_dataloaders(
        DATASET_PATH, BATCH_SIZE)

    # Step 3: Load model
    print("\n[3/6] Loading trained model...")
    model = load_model(CHECKPOINT, device)

    # Step 4: Get predictions
    print("\n[4/6] Running inference on test set...")
    true_labels, pred_labels, probs = get_predictions(
        model, test_loader, device)

    print(f"  Test samples evaluated: {len(true_labels)}")

    # Step 5: Confusion matrix
    print("\n[5/6] Generating confusion matrix...")
    cm, cm_pct = plot_confusion_matrix(true_labels, pred_labels)

    # Step 6: All metrics
    print("\n[6/6] Computing metrics...")
    precisions, recalls, f1s = print_detailed_metrics(
        true_labels, pred_labels)

    plot_metrics_chart(precisions, recalls, f1s)
    severity_report(true_labels, pred_labels, probs)
    confidence_analysis(true_labels, pred_labels, probs)

    print("\n  evaluate.py complete ✅")
    print("  Check ai-models/outputs/ for all charts")
    print("\n  Pipeline complete:")
    print("  explore → preprocess → augment →"
          " dataset → train → evaluate ✅")