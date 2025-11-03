# ===========================================================
# MASTER AGENT (EVAL MODE) — Safe read-only version (v2)
# Extract → Retrieve → Reason → Print results only
# Adds: unit extraction, OOD gating, abstention, thresholds
# ===========================================================

import os, re, json, time, glob, csv, requests
import numpy as np
from dotenv import load_dotenv
from rdflib import Graph, Namespace, RDF

# ---------------- CONFIG ----------------
load_dotenv()
AALTO_KEY = os.getenv("AALTO_KEY")
if not AALTO_KEY:
    raise EnvironmentError("Please set AALTO_KEY in your .env file.")

TTL_FILES = None            # None = auto-detect all OEM*_OEM.ttl
TOP_K = 5
SLEEP_BETWEEN_CALLS = 1.3      # seconds between each variable reasoning call
MAX_RETRIES = 2
BACKOFF = 8                    # seconds backoff on rate limit
SHOW_ONLY_SUMMARY = True
SHACL_RULES = None

# --- API endpoints ---
EMBED_URL = "https://aalto-openai-apigw.azure-api.net/v1/openai/text-embedding-3-large/embeddings"
LLM_URL   = "https://aalto-openai-apigw.azure-api.net/v1/openai/deployments/gpt-4.1-2025-04-14/chat/completions"
HEADERS   = {"Content-Type": "application/json", "Ocp-Apim-Subscription-Key": AALTO_KEY}

# --- ontology store (pre-embedded) ---
ONTO_VECS = "ontology_vectors.npy"
ONTO_IDS  = "ontology_ids.json"
ONTO_TXTS = "ontology_texts.json"

# --- namespaces ---
sosa = Namespace("http://www.w3.org/ns/sosa/")
fmu  = Namespace("http://example.com/fmu#")
qudt = Namespace("http://qudt.org/2.1/schema/qudt#")

# ===========================================================
# UTILITIES
# ===========================================================

def embed_text_online(text, dim=3072):
    payload = {"input": text, "model": "text-embedding-3-large"}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.post(EMBED_URL, headers=HEADERS, json=payload, timeout=45)
            if r.status_code == 200:
                return np.array(r.json()["data"][0]["embedding"], dtype=np.float32)
            elif r.status_code == 429:
                print(f"⚠️  Rate limit hit, sleeping {BACKOFF}s (attempt {attempt})")
                time.sleep(BACKOFF)
                continue
            else:
                print(f"Embedding API error ({r.status_code}) — fallback to zero vector.")
        except requests.exceptions.RequestException:
            print(f"Network issue (attempt {attempt}) — retrying…")
            time.sleep(5)
    return np.zeros(dim, dtype=np.float32)


def cosine_similarity(vec, mat):
    denom = np.linalg.norm(vec)
    if (denom == 0) or (not np.isfinite(denom)):
        return np.zeros(mat.shape[0], dtype=np.float32)
    v = vec / denom
    Mnorms = np.linalg.norm(mat, axis=1, keepdims=True)
    M = np.divide(mat, Mnorms, out=np.zeros_like(mat), where=(Mnorms != 0))
    sims = np.dot(M, v)
    sims[~np.isfinite(sims)] = 0.0
    return sims


def reason_best_match(var, query_text, top_matches):
    prompt = f"""
You are a reasoning agent mapping OEM variables to ontology concepts.

Variable metadata:
{query_text}

Candidates:
{json.dumps(top_matches, indent=2)}

Guidelines:
- Expand abbreviations (P→Power, T→Torque, n/omega→RotationalSpeed, EAR→Expanded Area Ratio).
- Choose exactly one candidate ID matching meaning, unit, and domain.
- If none clearly match, leave best_match empty and confidence 0.0.

Return strict JSON ONLY:
{{
  "original": "{var}",
  "best_match": "<ontology_id or empty>",
  "confidence": <0.0-1.0>,
  "reason": "<short>"
}}
"""
    for attempt in range(1, MAX_RETRIES + 1):
        r = requests.post(LLM_URL, headers=HEADERS, json={
            "model": "gpt-4.1-2025-04-14",
            "messages": [
                {"role": "system", "content": "Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }, timeout=120)

        if r.status_code == 429:
            print(f"⚠️  Hit rate limit — sleeping {BACKOFF}s (attempt {attempt})")
            time.sleep(BACKOFF)
            continue
        elif r.status_code != 200:
            return {"original": var, "best_match": "", "confidence": 0.0, "reason": f"API {r.status_code}"}

        try:
            content = r.json()["choices"][0]["message"]["content"]
            start, end = content.find("{"), content.rfind("}") + 1
            return json.loads(content[start:end])
        except Exception:
            return {"original": var, "best_match": "", "confidence": 0.0, "reason": "parse error"}
    return {"original": var, "best_match": "", "confidence": 0.0, "reason": "max retries"}


# ===========================================================
# ENHANCED FILTERS: Units, OOD, Abstain Logic
# ===========================================================

MIN_SIM = 0.45
SIM_GAP = 0.06
OOD_PATTERNS = [
    r"\bPkt", r"\bPLC", r"\bFW[_-]", r"\bDbgVar",
    r"\bMemTemp", r"\bCabTemp", r"\bChecksum", r"\bVibAlarm"
]

UNIT_EQUIV = {
    "rpm": {"REV-PER-MIN", "RPM"},
    "rev/s": {"REV-PER-SEC", "RPS"},
    "kN": {"KiloN", "KN"},
    "kNm": {"KiloN-M", "KNM"},
    "m": {"M"},
    "Nm3": {"NM3", "Normal_m3"},
    "degC": {"DEG", "C"}
}

def normalize_unit_token(u: str) -> str:
    if not u:
        return ""
    u = u.replace("unit:", "").replace("#", "").upper()
    for canon, variants in UNIT_EQUIV.items():
        if u in variants:
            return canon
    return ""

def infer_unit_from_varname(name: str) -> str:
    if not name:
        return ""
    n = name.lower()
    if "_rpm" in n: return "rpm"
    if "_rps" in n or "revpersec" in n: return "rev/s"
    if "_knm" in n: return "kNm"
    if "_kn" in n: return "kN"
    if "_nm3" in n: return "Nm3"
    if "_m" in n: return "m"
    if "degc" in n or "_c" in n: return "degC"
    return ""

def unit_from_candidate_id(cid: str) -> str:
    if not cid:
        return ""
    c = cid.lower()
    if c.endswith("_rpm"): return "rpm"
    if "revpersec" in c: return "rev/s"
    if c.endswith("_knm"): return "kNm"
    if c.endswith("_kn"): return "kN"
    if c.endswith("_m"): return "m"
    if c.endswith("_nm3"): return "Nm3"
    if c.endswith("_degc"): return "degC"
    return ""

def unit_compat_score(orig: str, cand: str) -> float:
    if not orig and not cand:
        return 1.0
    if orig == cand:
        return 1.0
    if {orig, cand} == {"rpm", "rev/s"}:
        return 0.85
    if not orig or not cand:
        return 0.8
    return 0.5

def is_ood(name: str) -> bool:
    if not name:
        return False
    return any(re.search(p, name, re.IGNORECASE) for p in OOD_PATTERNS)


# ===========================================================
# MAIN
# ===========================================================

def run_eval():
    files = TTL_FILES if TTL_FILES else sorted(glob.glob("OEM*_OEM.ttl"))
    onto_vecs = np.load(ONTO_VECS)
    onto_ids  = json.load(open(ONTO_IDS))
    onto_txts = json.load(open(ONTO_TXTS))
    dim = onto_vecs.shape[1]

    results = []

    for ttl in files:
        base = os.path.splitext(os.path.basename(ttl))[0]
        print(f"\n================= Processing {ttl} =================")
        g = Graph(); g.parse(ttl, format="turtle")

        vars_list = []
        for s,_,_ in g.triples((None, RDF.type, sosa.ObservableProperty)):
            name = None
            for _,_,o in g.triples((s, fmu.hasFMUVariableName, None)):
                name = str(o)
            u_val = ""
            for _,_,u in g.triples((s, qudt.unit, None)):
                u_val = str(u)
            unit_tok = normalize_unit_token(u_val) or infer_unit_from_varname(name)
            vars_list.append({"id": str(s), "name": name, "unit": unit_tok})
        print(f"  Extracted {len(vars_list)} vars")

        # loop variables
        for v in vars_list:
            # --- OOD keyword rejection ---
            if is_ood(v["name"]):
                results.append({
                    "file": base,
                    "original_name": v["name"],
                    "best_match": "",
                    "confidence": 0.0,
                    "reason": "Rejected by OOD keyword gate"
                })
                print(f"  → {v['name']} → (no match) [OOD]")
                continue

            query = f"Variable '{v['name']}' from OEM dataset"
            if v["unit"]:
                query += f" [unit={v['unit']}]"

            vec = embed_text_online(query, dim)
            sims = cosine_similarity(vec, onto_vecs)

            # adjust by unit compatibility
            adj_sims = []
            for i, sim in enumerate(sims):
                cu = unit_from_candidate_id(onto_ids[i])
                w = unit_compat_score(v["unit"], cu)
                adj_sims.append(sim * w)
            adj_sims = np.array(adj_sims)
            idx = np.argsort(adj_sims)[::-1]
            top_idx = idx[:TOP_K]
            top_adj = adj_sims[top_idx]
            tops = [{"id": onto_ids[i], "similarity": float(top_adj[j]), "text": onto_txts[i]} for j,i in enumerate(top_idx)]

            # low-sim abstain
            if len(top_adj)==0 or top_adj[0] < MIN_SIM:
                results.append({
                    "file": base,
                    "original_name": v["name"],
                    "best_match": "",
                    "confidence": 0.0,
                    "reason": f"Low similarity ({top_adj[0] if len(top_adj) else 0:.2f} < {MIN_SIM})"
                })
                print(f"  → {v['name']} → (no match) [low-sim]")
                continue

            # strong top gap -> auto-pick
            if len(top_adj) >= 2 and (top_adj[0] - top_adj[1]) >= SIM_GAP:
                top_id = tops[0]["id"]
                conf = float(min(0.99, max(0.5, top_adj[0])))
                results.append({
                    "file": base,
                    "original_name": v["name"],
                    "best_match": top_id,
                    "confidence": conf,
                    "reason": "Auto-picked by adjusted similarity margin"
                })
                print(f"  → {v['name']} → {top_id} (conf={conf:.2f}) [auto]")
                time.sleep(SLEEP_BETWEEN_CALLS)
                continue

            # ambiguous case → ask LLM
            res = reason_best_match(v["name"], query, tops)
            cu = unit_from_candidate_id(res.get("best_match",""))
            if res.get("best_match") and unit_compat_score(v["unit"], cu) < 0.7:
                res = {"original": v["name"], "best_match": "", "confidence": 0.0,
                       "reason": "Abstained: incompatible units"}

            results.append({
                "file": base,
                "original_name": v["name"],
                "best_match": res.get("best_match",""),
                "confidence": float(res.get("confidence", 0.0)),
                "reason": res.get("reason","")
            })
            print(f"  → {v['name']} → {res.get('best_match','')} (conf={float(res.get('confidence',0.0)):.2f})")
            time.sleep(SLEEP_BETWEEN_CALLS)

    # write results
    with open("eval_results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file","original_name","best_match","confidence","reason"])
        w.writeheader()
        w.writerows(results)
    print("✅ Saved results → eval_results.csv")

    # summary
    print("\n📊 === SUMMARY ===")
    total = len(results)
    high = sum(1 for r in results if r["confidence"] >= 0.7)
    low  = sum(1 for r in results if 0.4 <= r["confidence"] < 0.7)
    none = sum(1 for r in results if r["confidence"] < 0.4)
    print(f" Total variables: {total}")
    print(f" High confidence (≥0.7): {high}")
    print(f" Low confidence (0.4–0.7): {low}")
    print(f" No match (<0.4): {none}")

    print("\nExample outputs:")
    for r in results[:5]:
        print(json.dumps(r, indent=2))


# ===========================================================
if __name__ == "__main__":
    run_eval()
