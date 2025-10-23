import pandas as pd

# ground truth (what you showed)
truth = pd.DataFrame({
    "oem_file":["OEMA_OEM.ttl","OEMA_OEM.ttl"],
    "original_name":["MainEngPower_kW","RidgeLoad_kN"],
    "canonical_id":["mcrPower_kW","Ftr_kN"]
})

# model output (your eval_results.csv style: file missing ".ttl")
pred = pd.DataFrame({
    "file":["OEMA_OEM","OEMA_OEM"],
    "original_name":["MainEngPower_kW","RidgeLoad_kN"],
    "best_match":["mcrPower_kW","Ftr_kN"],
    "confidence":[0.52,0.54]
})

# ✅ normalize file names to same key: base without ".ttl", case-insensitive
truth["oem_file_norm"] = truth["oem_file"].str.strip().str.replace(r"\.ttl$","",regex=True).str.lower()
pred["file_norm"]      = pred["file"].str.strip().str.replace(r"\.ttl$","",regex=True).str.lower()

# join on normalized keys + variable name
m = pred.merge(truth, how="left",
               left_on=["file_norm","original_name"],
               right_on=["oem_file_norm","original_name"])

# normalize labels for comparison
m["best_match_norm"]   = m["best_match"].fillna("").str.strip().str.lower()
m["canonical_id_norm"] = m["canonical_id"].fillna("").str.strip().str.lower()
m["is_correct"]        = m["best_match_norm"] == m["canonical_id_norm"]

print(m[["file","oem_file","original_name","best_match","canonical_id","is_correct"]])
