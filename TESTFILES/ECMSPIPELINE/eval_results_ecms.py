#!/usr/bin/env python3
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

# ---------------- CONFIG ----------------
RESULTS_CSV = Path("eval_results_ecms_clean.csv")
GT_XLSX = Path("CorrectNamesMappings.xlsx")
GT_SHEET = None   # set sheet name if needed (e.g., "Sheet1")
OUT_DIR = Path("eval_outputs")
OUT_DIR.mkdir(exist_ok=True)

# ---------------- LOAD DATA ----------------
res = pd.read_csv(RESULTS_CSV)

# Normalize key columns
for c in ["original_name", "best_match", "status"]:
    if c in res.columns:
        res[c] = res[c].astype(str).str.strip()

# clean best_match empties
res["best_match"] = res["best_match"].replace({"nan": "", "None": ""}).fillna("").astype(str).str.strip()

# ---------------- LOAD GROUND TRUTH (robust) ----------------
gt_raw = pd.read_excel(GT_XLSX, sheet_name=GT_SHEET)

if isinstance(gt_raw, dict):
    first_sheet = next(iter(gt_raw.keys()))
    print(f"ℹ️ sheet_name=None -> using first sheet: {first_sheet}")
    gt_df = gt_raw[first_sheet]
else:
    gt_df = gt_raw

# take first 2 columns (or adjust if your headers exist)
gt_df = gt_df.iloc[:, :2].copy()
gt_df.columns = ["original_name", "correct_match"]
gt_df["original_name"] = gt_df["original_name"].astype(str).str.strip()
gt_df["correct_match"] = gt_df["correct_match"].astype(str).str.strip()
gt_df["correct_match"] = gt_df["correct_match"].replace({"nan": "", "None": ""}).fillna("").astype(str).str.strip()

# ---------------- BUILD GT MAP ----------------
gt_map = (
    gt_df.dropna(subset=["original_name"])
         .set_index("original_name")["correct_match"]
         .to_dict()
)
print(f"✅ Ground truth mappings loaded: {len(gt_map)}")

# ---------------- ATTACH GROUND TRUTH ----------------
res["correct_match"] = res["original_name"].map(gt_map).fillna("").astype(str).str.strip()
res["has_gt"] = res["correct_match"].ne("")

missing_in_gt = res.loc[~res["has_gt"], "original_name"].unique().tolist()
(Path(OUT_DIR / "missing_in_ground_truth.txt")).write_text("\n".join(missing_in_gt))
print(f"⚠️ Missing in ground truth: {len(missing_in_gt)} (saved to missing_in_ground_truth.txt)")

# ---------------- HELPERS ----------------
def is_correct_prediction(row) -> bool:
    """Correct if we have GT and best_match equals correct_match."""
    if not row["has_gt"]:
        return False
    return str(row["best_match"]).strip() == str(row["correct_match"]).strip()

def should_accept(row) -> bool:
    """
    "Should be accepted" means: has GT and correct_match is non-empty.
    In your current dataset this is basically the definition of "actual positive".
    """
    return bool(row["has_gt"]) and (str(row["correct_match"]).strip() != "")

# ---------------- ROUTING SPLITS ----------------
accepted = res[res["status"] == "ACCEPT"].copy()
human = res[res["status"] == "HUMAN_REVIEW"].copy()
nomatch = res[res["status"] == "NO_MATCH"].copy()

# ACCEPT -> correct vs wrong
accepted["is_correct"] = accepted.apply(is_correct_prediction, axis=1)
accepted_correct = int(accepted["is_correct"].sum())
accepted_wrong = int(len(accepted) - accepted_correct)  # wrong auto accepts (FP)

# NO_MATCH -> correct reject vs should-have-accepted (false reject)
nomatch["should_accept"] = nomatch.apply(should_accept, axis=1)
rejected_should_accept = int(nomatch["should_accept"].sum())          # false rejects
rejected_correct_reject = int(len(nomatch) - rejected_should_accept)  # correct rejects

# HUMAN_REVIEW -> should accept vs should reject
human["should_accept"] = human.apply(is_correct_prediction, axis=1)
human_should_accept = int(human["should_accept"].sum())
human_should_reject = int(len(human) - human_should_accept)

# Totals
n_accept = int(len(accepted))
n_human = int(len(human))
n_nomatch = int(len(nomatch))
n_total = int(len(res))

# ============================================================
# ✅ AUTO-ONLY CONFUSION MATRIX (EXCLUDES HUMAN_REVIEW)
# Predicted Positive = ACCEPT
# Predicted Negative = NO_MATCH
# Actual Positive = has_gt (correct_match exists)
# Actual Negative = no_gt (rare in your case)
# ============================================================
auto = res[res["status"].isin(["ACCEPT", "NO_MATCH"])].copy()

def classify_auto(row):
    actual_pos = bool(row["has_gt"])  # GT exists => there is a correct mapping
    pred_pos = (row["status"] == "ACCEPT")

    if pred_pos:
        # ACCEPT: TP if correct mapping else FP
        if actual_pos and is_correct_prediction(row):
            return "TP"
        else:
            return "FP"
    else:
        # NO_MATCH: FN if there WAS a GT mapping (actual_pos), else TN
        if actual_pos:
            return "FN"
        else:
            return "TN"

auto["confusion_auto"] = auto.apply(classify_auto, axis=1)
counts_auto = auto["confusion_auto"].value_counts()

TP = int(counts_auto.get("TP", 0))
FP = int(counts_auto.get("FP", 0))
FN = int(counts_auto.get("FN", 0))
TN = int(counts_auto.get("TN", 0))

precision = TP / (TP + FP) if (TP + FP) else 0.0
recall = TP / (TP + FN) if (TP + FN) else 0.0
f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

# ---------------- REPORT ----------------
report = f"""
================ ECMS EVALUATION =================

Total evaluated rows: {n_total}
Ground-truth-covered rows: {int(res['has_gt'].sum())}
Missing in GT: {len(missing_in_gt)}

AUTO-ONLY CONFUSION (EXCLUDES HUMAN_REVIEW)
  (ACCEPT vs NO_MATCH only; HUMAN_REVIEW excluded)

Confusion matrix:
  TP: {TP}
  FP: {FP}
  FN: {FN}
  TN: {TN}

Auto-only metrics:
  Precision: {precision:.3f}
  Recall:    {recall:.3f}
  F1-score:  {f1:.3f}

Routing totals:
  ACCEPT:       {n_accept}
  HUMAN_REVIEW: {n_human}
  NO_MATCH:     {n_nomatch}

Requested breakdowns:
  ACCEPT -> correct: {accepted_correct}
  ACCEPT -> wrong (FP): {accepted_wrong}

  NO_MATCH (rejected) -> correct rejects: {rejected_correct_reject}
  NO_MATCH (rejected) -> should have been accepted (false rejects): {rejected_should_accept}

  HUMAN_REVIEW -> should accept: {human_should_accept}
  HUMAN_REVIEW -> should reject: {human_should_reject}

==================================================
"""
print(report)
(Path(OUT_DIR / "evaluation_report.txt")).write_text(report)

# ---------------- PLOTS ----------------
sns.set_theme(style="whitegrid")

# 0) Auto-only confusion matrix plot (clean labels)
# Rows = actual, cols = predicted
# [[TP, FN],
#  [FP, TN]]
cm = [[TP, FN],
      [FP, TN]]

cm_df = pd.DataFrame(
    cm,
    index=["Actual Positive", "Actual Negative"],
    columns=["Pred ACCEPT", "Pred NO_MATCH"]
)

plt.figure(figsize=(7.2, 5.6))
ax = sns.heatmap(
    cm_df,
    annot=True,
    fmt="d",
    cmap="Blues",
    cbar=True,
    square=True,
    linewidths=0.5,
    linecolor="white"
)
ax.set_title("ECMS Auto-Only Confusion Matrix (ACCEPT vs NO_MATCH)", pad=12)
ax.set_xlabel("Predicted")
ax.set_ylabel("Actual")
ax.set_xticklabels(ax.get_xticklabels(), rotation=0, ha="center")
ax.set_yticklabels(ax.get_yticklabels(), rotation=0, va="center")
plt.tight_layout()
plt.savefig(OUT_DIR / "confusion_matrix_auto_only.png", dpi=250, bbox_inches="tight")
plt.close()

# 1) ACCEPT total vs wrong accepted (FP) (stacked bar)
plt.figure(figsize=(7, 5))
x = ["ACCEPT"]
plt.bar(x, [accepted_correct], label="Correct ACCEPT")
plt.bar(x, [accepted_wrong], bottom=[accepted_correct], label="Wrong ACCEPT (FP)")
plt.ylabel("Count")
plt.title("Auto-Accept Outcomes")
plt.legend()
plt.tight_layout()
plt.savefig(OUT_DIR / "figure_1_accept_correct_vs_fp.png", dpi=200)
plt.close()

# 2) NO_MATCH outcomes (stacked bar)
plt.figure(figsize=(8, 5))
x = ["NO_MATCH (Rejected)"]
plt.bar(x, [rejected_correct_reject], label="Correct Reject")
plt.bar(x, [rejected_should_accept], bottom=[rejected_correct_reject], label="Should ACCEPT (False Reject)")
plt.ylabel("Count")
plt.title("Reject Outcomes (NO_MATCH)")
plt.legend()
plt.tight_layout()
plt.savefig(OUT_DIR / "figure_2_reject_correct_vs_false_reject.png", dpi=200)
plt.close()

# 3) Routing outcomes + HR breakdown (stacked per routing bucket)
categories = ["ACCEPT", "NO_MATCH", "HUMAN_REVIEW"]
good = [accepted_correct, rejected_correct_reject, human_should_accept]
bad  = [accepted_wrong,   rejected_should_accept, human_should_reject]

plt.figure(figsize=(10, 6))
plt.bar(categories, good, label="Correct / Good outcome")
plt.bar(categories, bad, bottom=good, label="Wrong / Needs change")
plt.ylabel("Count")
plt.title("Routing Outcomes + Human Review Breakdown")
plt.legend()
plt.tight_layout()
plt.savefig(OUT_DIR / "figure_3_routing_outcomes_breakdown.png", dpi=200)
plt.close()

# 4) Simple routing distribution (counts)
plt.figure(figsize=(8, 5))
res["status"].value_counts().reindex(["ACCEPT", "HUMAN_REVIEW", "NO_MATCH"]).fillna(0).plot(kind="bar")
plt.title("Routing Distribution (Counts)")
plt.ylabel("Count")
plt.tight_layout()
plt.savefig(OUT_DIR / "routing_distribution.png", dpi=200)
plt.close()

# ---------------- SAVE OUTPUT FILES ----------------
res.to_csv(OUT_DIR / "eval_results_scored.csv", index=False)
auto.to_csv(OUT_DIR / "eval_results_auto_only_scored.csv", index=False)

routing_summary = pd.DataFrame({
    "status": ["ACCEPT", "NO_MATCH", "HUMAN_REVIEW"],
    "total":  [n_accept, n_nomatch, n_human],
    "good":   [accepted_correct, rejected_correct_reject, human_should_accept],
    "bad":    [accepted_wrong, rejected_should_accept, human_should_reject],
})
routing_summary.to_csv(OUT_DIR / "routing_summary.csv", index=False)

print("✅ Evaluation complete. Outputs saved in:", OUT_DIR.resolve())
print("🖼️ Figures saved:")
print("  - confusion_matrix_auto_only.png")
print("  - figure_1_accept_correct_vs_fp.png")
print("  - figure_2_reject_correct_vs_false_reject.png")
print("  - figure_3_routing_outcomes_breakdown.png")
print("  - routing_distribution.png")
print("📄 Reports saved:")
print("  - evaluation_report.txt")
print("  - missing_in_ground_truth.txt")
print("  - routing_summary.csv")
print("  - eval_results_scored.csv")
print("  - eval_results_auto_only_scored.csv")
