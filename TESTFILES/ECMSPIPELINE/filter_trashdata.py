import os
import pandas as pd

# ---------------- CONFIG (edit if needed) ----------------
HERE = os.path.dirname(os.path.abspath(__file__))

MAPPINGS_XLSX = os.path.join(HERE, "Mappings.xlsx")  # if script is in ECMSPIPELINE folder
MODEL_RESULTS = os.path.join(HERE, "eval_results_ecms.csv")
AUDIT_RESULTS = os.path.join(HERE, "routing_audit_ecms.csv")

OUT_MODEL_FILTERED   = os.path.join(HERE, "eval_results_ecms_filtered.csv")
OUT_AUDIT_FILTERED   = os.path.join(HERE, "routing_audit_ecms_filtered.csv")
OUT_MODEL_EXCLUDED   = os.path.join(HERE, "eval_results_ecms_excluded_not_found.csv")
OUT_AUDIT_EXCLUDED   = os.path.join(HERE, "routing_audit_ecms_excluded_not_found.csv")

NOT_FOUND_PHRASE = "not found in standard"

# ---------------- HELPERS ----------------
def norm_file(x: str) -> str:
    x = "" if pd.isna(x) else str(x).strip().lower()
    if x.endswith(".ttl"):
        x = x[:-4]
    return x

def norm_name(x: str) -> str:
    return "" if pd.isna(x) else str(x).strip().lower()

def find_col(df, candidates):
    cols = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in cols:
            return cols[cand.lower()]
    return None

def row_contains_not_found(row) -> bool:
    # Check all cells in row for the phrase
    for v in row:
        if pd.isna(v):
            continue
        if NOT_FOUND_PHRASE in str(v).lower():
            return True
    return False


# ---------------- LOAD MODEL RESULTS ----------------
pred = pd.read_csv(MODEL_RESULTS)
audit = pd.read_csv(AUDIT_RESULTS)

# normalize keys for model csvs
pred["file_norm"] = pred["file"].apply(norm_file) if "file" in pred.columns else ""
pred["original_name_norm"] = pred["original_name"].apply(norm_name) if "original_name" in pred.columns else ""

audit["file_norm"] = audit["file"].apply(norm_file) if "file" in audit.columns else ""
audit["original_name_norm"] = audit["original_name"].apply(norm_name) if "original_name" in audit.columns else ""

# ---------------- LOAD MAPPINGS.XLSX (ALL SHEETS) ----------------
sheets = pd.read_excel(MAPPINGS_XLSX, sheet_name=None)

# We will collect exclusion keys from all sheets.
exclude_pairs = set()   # (file_norm, original_name_norm)
exclude_names = set()   # original_name_norm (fallback if file column missing)

total_nf_rows = 0

for sheet_name, df in sheets.items():
    if df is None or df.empty:
        continue

    # Identify likely columns
    file_col = find_col(df, ["oem_file", "file", "filename", "oem", "ttl", "source_file"])
    name_col = find_col(df, ["original_name", "oem_variable", "variable", "var", "oem_name", "name"])

    # Find rows marked "Not found in standard"
    mask_nf = df.apply(row_contains_not_found, axis=1)
    nf = df[mask_nf].copy()
    if nf.empty:
        continue

    total_nf_rows += len(nf)

    # Extract keys
    if name_col is None:
        # If we can't find a variable name column, we can't build exclusion list from this sheet.
        # Still continue other sheets.
        continue

    nf["original_name_norm"] = nf[name_col].apply(norm_name)

    if file_col is not None:
        nf["file_norm"] = nf[file_col].apply(norm_file)
        for _, r in nf.iterrows():
            if r["file_norm"] and r["original_name_norm"]:
                exclude_pairs.add((r["file_norm"], r["original_name_norm"]))
            elif r["original_name_norm"]:
                exclude_names.add(r["original_name_norm"])
    else:
        # fallback: exclude by variable name only
        for v in nf["original_name_norm"].tolist():
            if v:
                exclude_names.add(v)

print(f"📌 Found {total_nf_rows} rows marked '{NOT_FOUND_PHRASE}' across Excel sheets.")
print(f"📌 Exclusion keys: {len(exclude_pairs)} (file+var), plus {len(exclude_names)} (var-only fallback).")

# ---------------- APPLY EXCLUSION ----------------
def should_exclude(df):
    # Prefer file+var matching, fallback to var-only
    pair_hit = df.apply(lambda r: (r["file_norm"], r["original_name_norm"]) in exclude_pairs, axis=1)
    name_hit = df["original_name_norm"].isin(exclude_names)
    return pair_hit | name_hit

pred_excl_mask = should_exclude(pred)
audit_excl_mask = should_exclude(audit)

pred_excluded = pred[pred_excl_mask].copy()
pred_filtered = pred[~pred_excl_mask].copy()

audit_excluded = audit[audit_excl_mask].copy()
audit_filtered = audit[~audit_excl_mask].copy()

# Drop helper columns from outputs (optional)
for df_out in (pred_excluded, pred_filtered, audit_excluded, audit_filtered):
    if "file_norm" in df_out.columns: df_out.drop(columns=["file_norm"], inplace=True)
    if "original_name_norm" in df_out.columns: df_out.drop(columns=["original_name_norm"], inplace=True)

# ---------------- WRITE OUTPUTS ----------------
pred_filtered.to_csv(OUT_MODEL_FILTERED, index=False)
audit_filtered.to_csv(OUT_AUDIT_FILTERED, index=False)

pred_excluded.to_csv(OUT_MODEL_EXCLUDED, index=False)
audit_excluded.to_csv(OUT_AUDIT_EXCLUDED, index=False)

print("\n✅ Wrote filtered (kept for evaluation):")
print("  -", OUT_MODEL_FILTERED)
print("  -", OUT_AUDIT_FILTERED)

print("\n🟨 Wrote excluded (Not found in standard):")
print("  -", OUT_MODEL_EXCLUDED)
print("  -", OUT_AUDIT_EXCLUDED)

print("\nCounts:")
print(f"  Model rows total:     {len(pred)}")
print(f"  Model rows kept:      {len(pred_filtered)}")
print(f"  Model rows excluded:  {len(pred_excluded)}")
print(f"  Audit rows total:     {len(audit)}")
print(f"  Audit rows kept:      {len(audit_filtered)}")
print(f"  Audit rows excluded:  {len(audit_excluded)}")
