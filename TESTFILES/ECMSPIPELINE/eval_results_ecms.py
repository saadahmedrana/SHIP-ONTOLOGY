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
res["best_match"] = res["best_match"].replace({"nan": "", "None": ""}).fillna("")

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
gt_df["correct_match"] = gt_df["correct_match"].replace({"nan": "", "None": ""}).fillna("")

# ---------------- BUILD GT MAP ----------------
gt_map = (
    gt_df.dropna(subset=["original_name"])
         .set_index("original_name")["correct_match"]
         .to_dict()
)
print(f"✅ Ground truth mappings loaded: {len(gt_map)}")

# ---------------- ATTACH GROUND TRUTH ----------------
res["correct_match"] = res["original_name"].map(gt_map).fillna("")
res["has_gt"] = res["correct_match"].astype(str).str.strip().ne("")

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
    "Should be accepted" means: has GT AND correct_match not empty.
    Since in your current setup everything has GT, this becomes:
    correct_match != "".
    """
    if not row["has_gt"]:
        return False
    return str(row["correct_match"]).strip() != ""

# ---------------- CONFUSION (STRICT; for legacy reporting) ----------------
# Pred Positive = ACCEPT ; Pred Negative = HUMAN_REVIEW or NO_MATCH
def classify_strict(row):
    if not row["has_gt"]:
        return "TN"
    if row["status"] == "ACCEPT":
        return "TP" if is_correct_prediction(row) else "FP"
    if row["status"] in ("HUMAN_REVIEW", "NO_MATCH"):
        return "FN"
    return "UNK"

res["confusion_strict"] = res.apply(classify_strict, axis=1)
counts = res["confusion_strict"].value_counts()
TP = counts.get("TP", 0)
FP = counts.get("FP", 0)
FN = counts.get("FN", 0)
TN = counts.get("TN", 0)

precision = TP / (TP + FP) if (TP + FP) else 0
recall = TP / (TP + FN) if (TP + FN) else 0
f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0

# ---------------- ROUTING ANALYSIS (what you asked) ----------------
accepted = res[res["status"] == "ACCEPT"].copy()
human = res[res["status"] == "HUMAN_REVIEW"].copy()
nomatch = res[res["status"] == "NO_MATCH"].copy()

# Accepted -> correct vs wrong
accepted["is_correct"] = accepted.apply(is_correct_prediction, axis=1)
accepted_correct = int(accepted["is_correct"].sum())
accepted_wrong = int(len(accepted) - accepted_correct)  # wrong auto accepts = FP under strict

# Rejected = NO_MATCH (explicit rejects) -> how many should have been accepted (false rejects)
# "Should accept" here: correct_match exists and non-empty
nomatch["should_accept"] = nomatch.apply(should_accept, axis=1)
rejected_should_accept = int(nomatch["should_accept"].sum())
rejected_correct_reject = int(len(nomatch) - rejected_should_accept)

# Human review -> how many would be correct if accepted (i.e., should accept)
human["would_be_correct_if_accepted"] = human.apply(is_correct_prediction, axis=1)
human_should_accept = int(human["would_be_correct_if_accepted"].sum())
human_should_reject = int(len(human) - human_should_accept)

# Totals
n_accept = int(len(accepted))
n_human = int(len(human))
n_nomatch = int(len(nomatch))
n_total = int(len(res))

# ---------------- REPORT ----------------
report = f"""
================ ECMS EVALUATION =================

Total evaluated rows: {n_total}
Ground-truth-covered rows: {int(res['has_gt'].sum())}
Missing in GT: {len(missing_in_gt)}

STRICT (ACCEPT vs non-ACCEPT) confusion:
  TP: {TP}
  FP: {FP}
  FN: {FN}
  TN: {TN}

Strict metrics:
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
# ---------------- CONFUSION MATRIX PLOT (CLEAN) ----------------
# Rows = actual, cols = predicted
# [[TP, FN],
#  [FP, TN]]
cm = [[TP, FN],
      [FP, TN]]

cm_df = pd.DataFrame(
    cm,
    index=["Positive", "Negative"],
    columns=["ACCEPT", "NON-ACCEPT"]
)

plt.figure(figsize=(7.5, 5.5))
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

ax.set_title("ECMS Strict Confusion Matrix (ACCEPT vs non-ACCEPT)", pad=12)
ax.set_xlabel("Predicted")
ax.set_ylabel("Actual")

# keep tick labels readable
ax.set_xticklabels(ax.get_xticklabels(), rotation=0, ha="center")
ax.set_yticklabels(ax.get_yticklabels(), rotation=0, va="center")

plt.tight_layout()
plt.savefig(OUT_DIR / "confusion_matrix_strict.png", dpi=250, bbox_inches="tight")
plt.close()


# 1) Figure: ACCEPT total vs wrong accepted (FP) (stacked bar)
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

# 2) Figure: REJECTED (NO_MATCH) total vs should-have-been-accepted (false rejects)
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

# 3) Figure: Total routing distribution + HR breakdown
# We'll do a grouped bar chart:
#   Bars: ACCEPT, NO_MATCH, HUMAN_REVIEW
#   For ACCEPT: correct vs wrong
#   For NO_MATCH: correct reject vs false reject
#   For HR: should accept vs should reject
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

# 4) Simple routing distribution (non-stacked) for quick view
plt.figure(figsize=(8, 5))
res["status"].value_counts().reindex(["ACCEPT", "HUMAN_REVIEW", "NO_MATCH"]).fillna(0).plot(kind="bar")
plt.title("Routing Distribution (Counts)")
plt.ylabel("Count")
plt.tight_layout()
plt.savefig(OUT_DIR / "routing_distribution.png", dpi=200)
plt.close()

# ---------------- SAVE SCORED CSV ----------------
res.to_csv(OUT_DIR / "eval_results_scored.csv", index=False)

# Extra: save a compact routing summary csv
routing_summary = pd.DataFrame({
    "status": ["ACCEPT", "NO_MATCH", "HUMAN_REVIEW"],
    "total":  [n_accept, n_nomatch, n_human],
    "good":   [accepted_correct, rejected_correct_reject, human_should_accept],
    "bad":    [accepted_wrong, rejected_should_accept, human_should_reject],
})
routing_summary.to_csv(OUT_DIR / "routing_summary.csv", index=False)

print("✅ Evaluation complete. Outputs saved in:", OUT_DIR.resolve())
print("🖼️ Figures saved:")
print("  - confusion_matrix_strict.png")
print("  - figure_1_accept_correct_vs_fp.png")
print("  - figure_2_reject_correct_vs_false_reject.png")
print("  - figure_3_routing_outcomes_breakdown.png")
print("  - routing_distribution.png")
print("📄 Reports saved:")
print("  - evaluation_report.txt")
print("  - missing_in_ground_truth.txt")
print("  - routing_summary.csv")
print("  - eval_results_scored.csv")
