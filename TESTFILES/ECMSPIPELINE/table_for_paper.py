#!/usr/bin/env python3
from pathlib import Path
import re
import pandas as pd
import matplotlib.pyplot as plt

SWEEP_ROOT = Path("sweep_results")
IN_CSV = SWEEP_ROOT / "sweep_summary.csv"

# Outputs
OUT_FULL_CSV       = SWEEP_ROOT / "sweep_table_full.csv"
OUT_COMPACT_CSV    = SWEEP_ROOT / "sweep_table_compact.csv"
OUT_TEX            = SWEEP_ROOT / "sweep_table_compact.tex"
OUT_TABLE_PNG      = SWEEP_ROOT / "sweep_table_compact.png"
OUT_PLOT_PNG       = SWEEP_ROOT / "metrics_vs_threshold.png"


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


def add_operational_rates(df: pd.DataFrame) -> pd.DataFrame:
    # total decisions = routed rows (after cleaning; i.e., excludes SKIPPED_NOT_IN_STANDARD)
    for c in ["ACCEPT_total", "HUMAN_REVIEW_total", "NO_MATCH_total"]:
        if c not in df.columns:
            df[c] = pd.NA

    df["total_decisions"] = (
        pd.to_numeric(df["ACCEPT_total"], errors="coerce").fillna(0) +
        pd.to_numeric(df["HUMAN_REVIEW_total"], errors="coerce").fillna(0) +
        pd.to_numeric(df["NO_MATCH_total"], errors="coerce").fillna(0)
    ).astype(int)

    hr = pd.to_numeric(df["HUMAN_REVIEW_total"], errors="coerce").fillna(0)
    tot = pd.to_numeric(df["total_decisions"], errors="coerce").replace(0, pd.NA)

    df["human_review_pct"] = (hr / tot) * 100.0
    return df


def write_latex_compact(t: pd.DataFrame, out_tex: Path):
    tex_table = t.to_latex(
        index=False,
        escape=True,
        float_format="%.3f",
        column_format="l" + "r" * (len(t.columns) - 1),
        longtable=False,
        bold_rows=False,
    )

    caption = "Threshold sweep results (AUTO-only confusion excludes HUMAN\\_REVIEW decisions)."
    label = "tab:threshold_sweep"

    wrapper = r"""\begin{table}[t]
\centering
\scriptsize
\setlength{\tabcolsep}{3.0pt}
\renewcommand{\arraystretch}{1.05}
\caption{""" + caption + r"""}
\label{""" + label + r"""}
\resizebox{\columnwidth}{!}{%
""" + tex_table.strip() + r"""
}
\end{table}
"""
    out_tex.write_text(wrapper, encoding="utf-8")


def table_to_png(t: pd.DataFrame, out_png: Path, title: str = None):
    # Create a clean table figure that fits a 2-column paper width.
    # Adjust fontsize/scale if needed.
    fig, ax = plt.subplots(figsize=(7.2, 1.6 + 0.28 * len(t)))
    ax.axis("off")

    if title:
        ax.set_title(title, fontsize=11, pad=6)

    # Convert values to strings (pretty)
    display = t.copy()
    for c in display.columns:
        display[c] = display[c].astype(str)

    tbl = ax.table(
        cellText=display.values,
        colLabels=list(display.columns),
        cellLoc="center",
        colLoc="center",
        loc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1.0, 1.15)

    # Light header emphasis
    for (r, c), cell in tbl.get_celld().items():
        cell.set_linewidth(0.3)
        if r == 0:
            cell.set_linewidth(0.6)
            cell.set_text_props(weight="bold")

    plt.tight_layout()
    plt.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    # Load or rebuild summary
    if not IN_CSV.exists():
        df = rebuild_sweep_summary(SWEEP_ROOT)
    else:
        df = pd.read_csv(IN_CSV)

    if "human_review_thr" not in df.columns:
        raise ValueError("Expected column 'human_review_thr' in sweep_summary.csv")

    df["human_review_thr"] = pd.to_numeric(df["human_review_thr"], errors="coerce")
    df = df.dropna(subset=["human_review_thr"]).sort_values("human_review_thr")

    # Add % sent to HUMAN_REVIEW
    df = add_operational_rates(df)
    df = safe_round(df, ["human_review_pct"], 1)

    # 1) FULL CSV (everything + operational rates)
    df.to_csv(OUT_FULL_CSV, index=False, encoding="utf-8")
    print(f"✅ Wrote {OUT_FULL_CSV}")

    # 2) COMPACT PAPER TABLE (keep it tight for 2-column)
    compact_cols = [
        "human_review_thr",
        "precision", "recall", "f1",
        "human_review_pct",
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
        "human_review_pct": "HR (%)",
        "ACCEPT_total": "Accept",
        "HUMAN_REVIEW_total": "Human",
        "NO_MATCH_total": "NoMatch",
        "TP": "TP",
        "FP": "FP",
        "FN": "FN",
        "TN": "TN",
    }
    t = t.rename(columns={k: v for k, v in rename.items() if k in t.columns})

    t.to_csv(OUT_COMPACT_CSV, index=False, encoding="utf-8")
    print(f"✅ Wrote {OUT_COMPACT_CSV}")

    # 3) LaTeX compact (2-col friendly)
    write_latex_compact(t, OUT_TEX)
    print(f"✅ Wrote {OUT_TEX}")

    # 4) Table as FIGURE (PNG)
    table_to_png(t, OUT_TABLE_PNG, title="Threshold sweep (compact)")
    print(f"✅ Wrote {OUT_TABLE_PNG}")

    # 5) Plot metrics vs threshold
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
    plt.savefig(OUT_PLOT_PNG, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Wrote {OUT_PLOT_PNG}")


if __name__ == "__main__":
    main()
