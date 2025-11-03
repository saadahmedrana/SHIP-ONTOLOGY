# ===========================================================
# EVALUATION SCRIPT — Model vs Ground Truth (report edition)
# ===========================================================
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay, precision_recall_fscore_support

# ---------------- CONFIG ----------------
GROUND_TRUTH = "master_mapping.csv"
MODEL_RESULTS = "eval_results.csv"

# ---------------- LOAD FILES ----------------
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

# ===========================================================
# GLOBAL METRICS
# ===========================================================
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

print("\n📊 === GLOBAL METRICS SUMMARY ===")
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

# --- Coverage, Abstention, OOD metrics ---
coverage = (merged['best_match_norm'] != "").mean()
abstention = 1 - coverage
ood_correct = ((merged['canonical_id_norm'] == "") & (merged['best_match_norm'] == "")).sum()
ood_total = (merged['canonical_id_norm'] == "").sum()
ood_accuracy = ood_correct / ood_total if ood_total else 0.0

print("\n🧾 === ADDITIONAL REPORT METRICS ===")
print(f"Model coverage (predicted something): {coverage*100:.1f}%")
print(f"Abstention rate (no prediction): {abstention*100:.1f}%")
print(f"OOD accuracy (correctly abstained): {ood_accuracy*100:.1f}%")

merged.to_csv("evaluation_detailed.csv", index=False)
print("✅ Saved detailed results → evaluation_detailed.csv")

# ===========================================================
# PER-DOMAIN PRECISION / RECALL / F1
# ===========================================================
def extract_domain(label):
    """Extracts domain prefix (e.g., 'prop', 'eng', 'comp') from canonical ID."""
    if pd.isna(label) or label == "":
        return "no_domain"
    if ":" in str(label):
        return label.split(":")[0]
    # if underscore pattern like prop_Thruster
    if "_" in str(label):
        prefix = label.split("_")[0]
        if prefix in ["prop", "eng", "comp", "mat", "unit"]:
            return prefix
    return "unknown"

merged['domain'] = merged['domain'].fillna("").astype(str)
merged['domain_extracted'] = merged['domain'].apply(lambda d: extract_domain(d) if d else "unknown")
# ===========================================================
# PER-DOMAIN PRECISION / RECALL / F1 (robust to mixed dtypes)
# ===========================================================
domain_stats = []
for domain, subset in merged.groupby('domain_extracted'):
    y_true = subset['canonical_id_norm'].astype(str).replace("nan", "")
    y_pred = subset['best_match_norm'].astype(str).replace("nan", "")
    mask = (y_true != "") | (y_pred != "")
    if mask.sum() == 0:
        continue

    y_true_clean = y_true[mask].fillna("").astype(str).tolist()
    y_pred_clean = y_pred[mask].fillna("").astype(str).tolist()

    # Compute micro-averaged precision/recall/F1 safely
    p, r, f, _ = precision_recall_fscore_support(
        y_true_clean, y_pred_clean,
        average='micro', zero_division=0
    )

    domain_stats.append((domain, round(p, 3), round(r, 3), round(f, 3), len(y_true_clean)))

print("\n🔬 === PER-DOMAIN PERFORMANCE ===")
if domain_stats:
    df_domains = pd.DataFrame(domain_stats, columns=["Domain","Precision","Recall","F1","Samples"])
    print(df_domains.to_string(index=False, float_format="%.3f"))
    df_domains.to_csv("per_domain_metrics.csv", index=False)
    print("📄 Saved per-domain metrics → per_domain_metrics.csv")
else:
    print("No domain data available for per-domain metrics.")


print("\n🔬 === PER-DOMAIN PERFORMANCE ===")
if domain_stats:
    df_domains = pd.DataFrame(domain_stats, columns=["Domain","Precision","Recall","F1","Samples"])
    print(df_domains.to_string(index=False, float_format="%.3f"))
    df_domains.to_csv("per_domain_metrics.csv", index=False)
    print("📄 Saved per-domain metrics → per_domain_metrics.csv")
else:
    print("No domain data available for per-domain metrics.")

# ===========================================================
# VISUALS
# ===========================================================
plt.figure(figsize=(10, 6), dpi=200)
plt.hist(merged.loc[merged['is_correct'], 'confidence'].dropna(), bins=12, alpha=0.7, label='Correct')
plt.hist(merged.loc[~merged['is_correct'], 'confidence'].dropna(), bins=12, alpha=0.7, label='Incorrect')
plt.title("Confidence Distribution: Correct vs Incorrect", fontsize=14)
plt.xlabel("Confidence", fontsize=12); plt.ylabel("Count", fontsize=12)
plt.legend(); plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("confidence_distribution.png", dpi=200)
plt.show()
# --- Confusion Matrix (with 'no_match') ---
merged['canonical_id_norm_filled'] = merged['canonical_id_norm'].replace("", "no_match")
merged['best_match_norm_filled'] = merged['best_match_norm'].replace("", "no_match")

y_true = merged['canonical_id_norm_filled'].astype(str).fillna("no_match")
y_pred = merged['best_match_norm_filled'].astype(str).fillna("no_match")

labels = sorted(set(map(str, y_true.tolist())) | set(map(str, y_pred.tolist())))
if "no_match" in labels:
    labels = [l for l in labels if l != "no_match"] + ["no_match"]

cm = confusion_matrix(y_true, y_pred, labels=labels)
fig, ax = plt.subplots(figsize=(18, 14), dpi=250)

disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=labels)
disp.plot(cmap='Blues', ax=ax, colorbar=False)

# ---- Enhanced readability tweaks ----
ax.set_title("Confusion Matrix — Including 'no_match'", fontsize=16, pad=20)
ax.set_xlabel("Predicted Label", fontsize=13, labelpad=10)
ax.set_ylabel("True Label", fontsize=13, labelpad=10)

# Rotate and format tick labels
ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right", fontsize=9)
ax.set_yticklabels(ax.get_yticklabels(), fontsize=9)

# Add grid lines for clarity
ax.grid(False)
for spine in ax.spines.values():
    spine.set_visible(False)

plt.tight_layout()
plt.savefig("confusion_matrix_readable.png", dpi=250, bbox_inches='tight')
plt.show()


# ===========================================================
# PER-FILE ACCURACY
# ===========================================================
per_file = merged.groupby('file')['is_correct'].mean().sort_values(ascending=False)
per_file.to_csv("per_file_accuracy.csv")
print("📄 Saved per-file accuracy → per_file_accuracy.csv")
