# ===========================================================
# EVALUATION SCRIPT — Model vs Ground Truth (robust + fixed)
# ===========================================================
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay

GROUND_TRUTH = "master_mapping.csv"
MODEL_RESULTS = "eval_results.csv"

truth = pd.read_csv(GROUND_TRUTH)
pred  = pd.read_csv(MODEL_RESULTS)

# --- Normalize file names and variable names ---
truth['oem_file_norm'] = truth['oem_file'].astype(str).str.strip().str.replace(r'\.ttl$', '', regex=True).str.lower()
pred['file_norm']      = pred['file'].astype(str).str.strip().str.replace(r'\.ttl$', '', regex=True).str.lower()

truth['original_name_norm'] = truth['original_name'].astype(str).str.strip().str.lower()
pred['original_name_norm']  = pred['original_name'].astype(str).str.strip().str.lower()

# --- Normalize canonical/predicted IDs ---
for df, col in [(truth, 'canonical_id'), (pred, 'best_match')]:
    df[col] = df[col].fillna("").astype(str).str.strip()

truth['canonical_id_norm'] = truth['canonical_id'].str.lower()
pred['best_match_norm']    = pred['best_match'].str.lower()

# ✅ --- Correct JOIN on normalized keys ---
merged = pred.merge(
    truth,
    how='left',
    left_on=['file_norm', 'original_name_norm'],
    right_on=['oem_file_norm', 'original_name_norm'],
    suffixes=('_pred', '_truth')
)

# --- Correctness ---
merged['is_correct'] = merged['best_match_norm'] == merged['canonical_id_norm']

# --- Metrics ---
tp = ((merged['canonical_id_norm'] != "") & merged['is_correct']).sum()
fp = ((merged['best_match_norm'] != "") & ~merged['is_correct']).sum()
fn = ((merged['canonical_id_norm'] != "") & (merged['best_match_norm'] == "")).sum()
tn = ((merged['canonical_id_norm'] == "") & (merged['best_match_norm'] == "")).sum()

total    = len(merged)
correct  = merged['is_correct'].sum()
accuracy = correct / total if total else 0.0
precision = tp / (tp + fp) if (tp + fp) else 0.0
recall    = tp / (tp + fn) if (tp + fn) else 0.0
f1        = (2*precision*recall)/(precision+recall) if (precision+recall) else 0.0

print("\n📊 === METRICS SUMMARY ===")
print(f"Total variables: {total}")
print(f"Correct matches: {correct}")
print(f"Accuracy: {accuracy:.3f}")
print(f"Precision: {precision:.3f}")
print(f"Recall: {recall:.3f}")
print(f"F1 Score: {f1:.3f}")

# --- Confidence stats ---
merged['confidence'] = pd.to_numeric(merged['confidence'], errors='coerce')
mean_conf_correct   = merged.loc[merged['is_correct'], 'confidence'].mean()
mean_conf_incorrect = merged.loc[~merged['is_correct'], 'confidence'].mean()
print(f"Mean confidence (correct): {0.0 if np.isnan(mean_conf_correct) else mean_conf_correct:.3f}")
print(f"Mean confidence (incorrect): {0.0 if np.isnan(mean_conf_incorrect) else mean_conf_incorrect:.3f}")

merged.to_csv("evaluation_detailed.csv", index=False)
print("✅ Saved detailed results → evaluation_detailed.csv")

# --- Visuals ---
plt.figure(figsize=(8,5))
plt.hist(merged.loc[merged['is_correct'], 'confidence'].dropna(), bins=12, alpha=0.7, label='Correct')
plt.hist(merged.loc[~merged['is_correct'], 'confidence'].dropna(), bins=12, alpha=0.7, label='Incorrect')
plt.title("Confidence Distribution: Correct vs Incorrect")
plt.xlabel("Confidence"); plt.ylabel("Count"); plt.legend(); plt.tight_layout()
plt.savefig("confidence_distribution.png"); plt.show()

# --- Confusion matrix ---
mask = (merged['canonical_id_norm'] != "") & (merged['best_match_norm'] != "")
y_true = merged.loc[mask, 'canonical_id_norm'].astype(str)
y_pred = merged.loc[mask, 'best_match_norm'].astype(str)
if len(y_true):
    labels = sorted(set(y_true.tolist()) | set(y_pred.tolist()))
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=labels).plot(cmap='Blues', xticks_rotation=90)
    plt.title("Confusion Matrix — Canonical vs Predicted")
    plt.tight_layout(); plt.savefig("confusion_matrix.png"); plt.show()
else:
    print("⚠️ Not enough overlapping labels to plot confusion matrix.")

# --- Per-file accuracy ---
per_file = merged.groupby('file')['is_correct'].mean().sort_values(ascending=False)
per_file.to_csv("per_file_accuracy.csv")
print("📄 Saved per-file accuracy → per_file_accuracy.csv")
