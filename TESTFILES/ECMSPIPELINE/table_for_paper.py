#!/usr/bin/env python3
from pathlib import Path
import re
import pandas as pd
import matplotlib.pyplot as plt

SWEEP_ROOT = Path("sweep_results")
IN_CSV = SWEEP_ROOT / "sweep_summary.csv"

# Outputs
OUT_COMPACT_CSV = SWEEP_ROOT / "sweep_table_compact.csv"
OUT_FULL_CSV    = SWEEP_ROOT / "sweep_table_full.csv"
OUT_TEX         = SWEEP_ROOT / "sweep_table_compact.tex"
OUT_PNG         = SWEEP_ROOT / "metrics_vs_threshold.png"

def extract_metrics_from_report(report_path: Path) -> dict:
    text = report_path.read_text(encoding="utf-8", errors="ignore")

    def grab(pattern, cast=float, default=None):
        m = re.search(pattern, text)
        return cast(m.group(1)) if m else default

    return {
        "TP": grab(r"\bTP:\s*(\d+)", int),
        "FP": grab(r"\bFP:\s*(\d+)", int),
        "FN": grab(r"\bFN:\s*(\d+)", int),
        "TN": grab(r"\bTN:\s*(\d+)", int),

        "precision": grab(r"Precision:\s*([0-9.]+)", float),
        "recall":    grab(r"Recall.*?:\s*([0-9.]+)", float),
        "f1":        grab(r"F1-score:\s*([0-9.]+)", float),
        "accuracy":  grab(r"Accuracy:\s*([0-9.]+)", float),
        "specificity": grab(r"Specificity.*?:\s*([0-9.]+)", float),
        "npv":         grab(r"\bNPV:\s*([0-9.]+)", float),
        "balanced_acc": grab(r"Balanced Acc:\s*([0-9.]+)", float),
        "mcc":         grab(r"\bMCC:\s*([0-9.\-]+)", float),

        "ACCEPT_total": grab(r"\bACCEPT:\s*(\d+)", int),
        "HUMAN_REVIEW_total": grab(r"\bHUMAN_REVIEW:\s*(\d+)", int),
        "NO_MATCH_total": grab(r"\bNO_MATCH:\s*(\d+)", int),

        "ACCEPT_correct": grab(r"ACCEPT -> correct:\s*(\d+)", int),
        "ACCEPT_wrong":   grab(r"ACCEPT -> wrong:\s*(\d+)", int),

        "NO_MATCH_correct": grab(r"NO_MATCH -> correct reject:\s*(\d+)", int),
        "NO_MATCH_should_accept": grab(r"NO_MATCH -> should-have-accepted:\s*(\d+)", int),

        "HR_should_accept": grab(r"HUMAN_REVIEW -> should accept:\s*(\d+)", int),
        "HR_should_reject": grab(r"HUMAN_REVIEW -> should reject:\s*(\d+)", int),
    }

def rebuild_sweep_summary(sweep_root: Path) -> pd.DataFrame:
    rows = []
    hr_dirs = sorted([p for p in sweep_root.iterdir() if p.is_dir() and p.name.startswith("hr_")])

    if not hr_dirs:
        raise FileNotFoundError(f"No hr_* folders found in {sweep_root.resolve()}")

    for d in hr_dirs:
        # threshold from folder name hr_0.50
        thr = float(d.name.split("_", 1)[1])

        report_path = d / "eval_outputs" / "evaluation_report.txt"
        if not report_path.exists():
            raise FileNotFoundError(f"Missing report: {report_path}")

        m = extract_metrics_from_report(report_path)
        m["human_review_thr"] = thr
        m["run_dir"] = str(d.resolve())
        rows.append(m)

    df = pd.DataFrame(rows).sort_values("human_review_thr")
    out_csv = sweep_root / "sweep_summary.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8")
    print(f"✅ Rebuilt {out_csv} from per-run evaluation_report.txt files")
    return df

def safe_round(df: pd.DataFrame, cols, ndigits=3):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").round(ndigits)
    return df

def main():
    # If sweep_summary.csv is missing, rebuild it from hr_*/eval_outputs/evaluation_report.txt
    if not IN_CSV.exists():
        df = rebuild_sweep_summary(SWEEP_ROOT)
    else:
        df = pd.read_csv(IN_CSV)

    if "human_review_thr" not in df.columns:
        raise ValueError("Expected column 'human_review_thr' in sweep_summary.csv")

    df["human_review_thr"] = pd.to_numeric(df["human_review_thr"], errors="coerce")
    df = df.dropna(subset=["human_review_thr"]).sort_values("human_review_thr")

    # 1) FULL CSV (keep everything)
    df.to_csv(OUT_FULL_CSV, index=False)
    print(f"✅ Wrote {OUT_FULL_CSV}")

    # 2) COMPACT TABLE (2-column paper friendly)
    compact_cols = [
        "human_review_thr",
        "precision", "recall", "f1",
        "ACCEPT_total", "HUMAN_REVIEW_total", "NO_MATCH_total",
        "TP", "FP", "FN", "TN",
    ]
    compact_cols = [c for c in compact_cols if c in df.columns]
    t = df[compact_cols].copy()
    t = safe_round(t, ["precision", "recall", "f1"], 3)

    rename = {
        "human_review_thr": "HR thr",
        "precision": "Prec.",
        "recall": "Rec.",
        "f1": "F1",
        "ACCEPT_total": "Accept",
        "HUMAN_REVIEW_total": "Human",
        "NO_MATCH_total": "NoMatch",
        "TP": "TP",
        "FP": "FP",
        "FN": "FN",
        "TN": "TN",
    }
    t = t.rename(columns={k: v for k, v in rename.items() if k in t.columns})
    t.to_csv(OUT_COMPACT_CSV, index=False)
    print(f"✅ Wrote {OUT_COMPACT_CSV}")

    # 3) LaTeX table compact
    tex_table = t.to_latex(
        index=False,
        escape=True,
        float_format="%.3f",
        column_format="l" + "r" * (len(t.columns) - 1),
        longtable=False,
        bold_rows=False,
    )

    caption = "Threshold sweep (AUTO-only confusion excludes HUMAN review decisions)."
    label = "tab:threshold_sweep"

    wrapper = r"""\begin{table}[t]
\centering
\scriptsize
\setlength{\tabcolsep}{3.5pt}
\renewcommand{\arraystretch}{1.05}
\caption{""" + caption + r"""}
\label{""" + label + r"""}
\resizebox{\columnwidth}{!}{%
""" + tex_table.strip() + r"""
}
\end{table}
"""
    OUT_TEX.write_text(wrapper, encoding="utf-8")
    print(f"✅ Wrote {OUT_TEX}")

    # 4) Plot metrics vs threshold
    x = df["human_review_thr"].to_numpy()
    prec = pd.to_numeric(df.get("precision"), errors="coerce").to_numpy()
    rec  = pd.to_numeric(df.get("recall"), errors="coerce").to_numpy()
    f1   = pd.to_numeric(df.get("f1"), errors="coerce").to_numpy()

    plt.figure(figsize=(7.0, 4.0))
    plt.plot(x, prec, marker="o", label="Precision")
    plt.plot(x, rec,  marker="s", label="Recall")
    plt.plot(x, f1,   marker="^", label="F1")
    plt.xlabel("HUMAN_REVIEW_THR")
    plt.ylabel("Score")
    plt.ylim(0.0, 1.0)
    plt.grid(True, linewidth=0.5, alpha=0.4)
    plt.legend(loc="best", frameon=True)
    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Wrote {OUT_PNG}")

if __name__ == "__main__":
    main()
