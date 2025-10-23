# ===========================================================
# MASTER AGENT — Full Automated Pipeline (multi-file ready)
# Extract → Retrieve → Reason → Rename
# ===========================================================

import os, re, json, time, csv, glob
import numpy as np
import requests
from dotenv import load_dotenv
from rdflib import Graph, Namespace, RDF, OWL, URIRef, Literal
from rdflib.namespace import PROV, XSD

# ---------------- CONFIG ----------------
load_dotenv()
AALTO_KEY = os.getenv("AALTO_KEY")
if not AALTO_KEY:
    raise EnvironmentError("Please set AALTO_KEY in your .env file.")

# Files to process:
# 1) If you want a single file test, set TTL_FILES = ["OEMA_OEM.ttl"] (for example).
# 2) Otherwise it will auto-detect all OEM* files.
TTL_FILES = None # None = auto-detect all OEM*_OEM.ttl; or set ["OEMA_OEM.ttl"]
TOP_K = 5
CONF_THRESHOLD = 0.5       # auto-accept confidence for renaming
SHACL_RULES = None         # set to "TRAFICOM_SHACL.ttl" when you want validation

# --- Aalto API endpoints ---
EMBED_URL = "https://aalto-openai-apigw.azure-api.net/v1/openai/text-embedding-3-large/embeddings"
LLM_URL   = "https://aalto-openai-apigw.azure-api.net/v1/openai/deployments/gpt-4.1-2025-04-14/chat/completions"
HEADERS   = {"Content-Type": "application/json", "Ocp-Apim-Subscription-Key": AALTO_KEY}

# --- ontology store (pre-embedded) ---
ONTO_VECS = "ontology_vectors.npy"
ONTO_IDS  = "ontology_ids.json"
ONTO_TXTS = "ontology_texts.json"

# --- namespaces ---
sosa = Namespace("http://www.w3.org/ns/sosa/")
ssn  = Namespace("http://www.w3.org/ns/ssn/")
fmu  = Namespace("http://example.com/fmu#")
ssp  = Namespace("http://example.com/ssp#")
qudt = Namespace("http://qudt.org/2.1/schema/qudt#")
prov = Namespace("http://www.w3.org/ns/prov#")
owl  = OWL

# ---------------- UTILITIES ----------------
def embed_text_online(text, dim=3072, retries=3, sleep=5):
    """Get an embedding from Aalto; robust retries; safe zero-vector fallback."""
    payload = {"input": text, "model": "text-embedding-3-large"}
    for attempt in range(1, retries + 1):
        try:
            r = requests.post(EMBED_URL, headers=HEADERS, json=payload, timeout=45)
            if r.status_code == 200:
                data = r.json()["data"][0]["embedding"]
                return np.array(data, dtype=np.float32)
            else:
                print(f"  Embedding API error ({r.status_code}): {r.text[:180]}")
        except requests.exceptions.RequestException:
            print(f"  Embedding connection attempt {attempt} failed — check VPN/network.")
        if attempt < retries:
            time.sleep(sleep)
    print("  Embedding API unreachable → using zero-vector fallback (results less reliable).")
    return np.zeros(dim, dtype=np.float32)

def cosine_similarity(vec, mat):
    """Cosine similarity with NaN/Inf safety."""
    denom = np.linalg.norm(vec)
    if (denom == 0) or (not np.isfinite(denom)):
        return np.zeros(mat.shape[0], dtype=np.float32)
    v = vec / denom
    Mnorms = np.linalg.norm(mat, axis=1, keepdims=True)
    M = np.divide(mat, Mnorms, out=np.zeros_like(mat), where=(Mnorms != 0))
    sims = M @ v
    # sanitize any potential numerical noise
    sims[~np.isfinite(sims)] = 0.0
    return sims.astype(np.float32)

def qudt_uri_to_label(u: str):
    if not u: return ""
    txt = str(u)
    mapping = {
        "unit:KiloW": "kW",
        "unit:KiloN-M": "kNm",
        "unit:REV-PER-MIN": "rpm",
        "unit:M3": "m³",
        "unit:MPa": "MPa",
        "unit:KiloN": "kN",
        "unit:HZ": "Hz",
    }
    for k, v in mapping.items():
        if k in txt:
            return v
    return txt.split("#")[-1]

def reason_best_match(var, query_text, top_matches):
    prompt = f"""
You are a reasoning agent mapping OEM variables to ontology concepts.

Variable metadata:
{query_text}

Candidates:
{json.dumps(top_matches, indent=2)}

Guidelines:
- Expand abbreviations (P→Power, T→Torque, omega/n→RotationalSpeed).
- Choose exactly one candidate ID matching meaning + unit + domain.
- If none clearly match, leave best_match empty and confidence 0.0.

Return strict JSON ONLY:
{{
  "original": "{var}",
  "best_match": "<ontology_id or empty>",
  "confidence": <0.0-1.0>,
  "reason": "<short>"
}}
"""
    payload = {
        "model": "gpt-4.1-2025-04-14",
        "messages": [
            {"role": "system", "content": "Output only valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    r = requests.post(LLM_URL, headers=HEADERS, json=payload, timeout=120)
    if r.status_code != 200:
        return {"original": var, "best_match": "", "confidence": 0.0, "reason": f"API {r.status_code}"}
    try:
        content = r.json()["choices"][0]["message"]["content"]
        start, end = content.find("{"), content.rfind("}") + 1
        return json.loads(content[start:end])
    except Exception:
        return {"original": var, "best_match": "", "confidence": 0.0, "reason": "parse error"}

# ---------------- PIPELINE STEPS ----------------
def extract_vars(ttl):
    g = Graph(); g.parse(ttl, format="turtle")
    vars_out = []
    for s, _p, _o in g.triples((None, RDF.type, None)):
        if (s, RDF.type, sosa.ObservableProperty) in g or (s, RDF.type, ssn.Property) in g:
            rec = {"id": str(s), "name": None, "context": None, "datatype": None, "unit": None, "value": None}
            for _a, _b, o in g.triples((s, fmu.hasFMUVariableName, None)): rec["name"] = str(o)
            for _a, _b, o in g.triples((s, ssp.hasVariableName, None)):   rec["name"] = str(o)
            for _a, _b, o in g.triples((s, ssn.isPropertyOf, None)):      rec["context"] = str(o)
            for _a, _b, o in g.triples((s, fmu.hasDataType, None)):       rec["datatype"] = str(o)
            for _a, _b, o in g.triples((s, ssp.hasDataType, None)):       rec["datatype"] = str(o)
            for _a, _b, o in g.triples((s, qudt.unit, None)):             rec["unit"] = str(o)
            for obs, _b, _c in g.triples((None, sosa.observedProperty, s)):
                for _x, _y, val in g.triples((obs, sosa.hasSimpleResult, None)):
                    try: rec["value"] = float(val)
                    except: rec["value"] = str(val)
            vars_out.append(rec)
    return vars_out

def build_query(v):
    hints = []
    lname = (v.get("name") or "").lower()
    if re.search(r"\bp[_\-]?(me|w)?\b", lname) or "power" in lname: hints.append("Likely ENGINE POWER.")
    if "omega" in lname or "rpm" in lname or "rev" in lname or "nn" in lname: hints.append("Likely ROTATIONAL SPEED.")
    if lname.startswith("t") or "torq" in lname: hints.append("Likely TORQUE.")
    if "bollard" in lname or "thrust" in lname: hints.append("Likely THRUST.")
    if "seachest" in lname or "ychest" in lname: hints.append("SEA CHEST VOLUME / COOLING WATER.")
    if "yield" in lname or "y_strength" in lname: hints.append("MATERIAL YIELD STRENGTH.")
    hint_txt = " ".join(hints)

    return (
        f"OEM variable name: '{v.get('name')}'. "
        f"Unit: {qudt_uri_to_label(v.get('unit')) or 'unspecified'}. "
        f"Context system IRI: {v.get('context')}. "
        f"Datatype: {v.get('datatype')}. "
        f"Observed value: {v.get('value')}. "
        f"{hint_txt}"
    )

def rename_with_conf(base, ttl_file, mappings, conf_thresh=CONF_THRESHOLD):
    out_file = f"{base}_corrected.ttl"
    g = Graph(); g.parse(ttl_file, format="turtle")
    changes, low_conf = 0, []
    for m in mappings:
        orig, best, conf = m.get("original"), m.get("best_match"), float(m.get("confidence", 0.0))
        if not best:
            continue
        if conf < conf_thresh:
            low_conf.append(m); continue
        for subj, _, val in g.triples((None, fmu.hasFMUVariableName, None)):
            if str(val) == str(orig):
                old = subj; new = URIRef(best)
                g.add((old, owl.sameAs, new))
                g.add((old, prov.confidence, Literal(conf, datatype=XSD.decimal)))
                changes += 1
    g.serialize(out_file, format="turtle")
    print(f"  Applied {changes} confident renames → {out_file}")
    if low_conf:
        with open(f"{base}_LowConfidence.json", "w", encoding="utf-8") as f:
            json.dump(low_conf, f, indent=2)
        print(f"  {len(low_conf)} low-confidence mappings saved for review.")
    return out_file

# ---------------- MAIN ----------------
def run_all():
    # auto-discover files if TTL_FILES not specified
    files = TTL_FILES if TTL_FILES else sorted(glob.glob("OEM*_OEM.ttl"))
    if not files:
        # fallback to Engine_Test1.ttl if present
        if os.path.exists("Engine_Test1.ttl"):
            files = ["Engine_Test1.ttl"]
        else:
            raise FileNotFoundError("No OEM*_OEM.ttl or Engine_Test1.ttl found in the current folder.")

    # ontology
    onto_vecs = np.load(ONTO_VECS)
    onto_ids  = json.load(open(ONTO_IDS, "r", encoding="utf-8"))
    onto_txts = json.load(open(ONTO_TXTS, "r", encoding="utf-8"))
    dim = onto_vecs.shape[1]

    combined_rows = []  # for combined_predictions.csv

    for ttl in files:
        base = os.path.splitext(os.path.basename(ttl))[0]
        print(f"\n================= Processing {ttl} =================")
        vars_list = extract_vars(ttl)
        print(f"  Extracted {len(vars_list)} vars")

        # retrieval + reasoning
        mappings = []
        for v in vars_list:
            q = build_query(v)
            vec = embed_text_online(q, dim=dim)
            sims = cosine_similarity(vec, onto_vecs)
            idx = np.argsort(sims)[::-1][:TOP_K]
            tops = [{"id": onto_ids[i], "similarity": float(sims[i]), "text": onto_txts[i]} for i in idx]
            res = reason_best_match(v["name"], q, tops)
            mappings.append(res)
            print(f"  → {v['name']} → {res['best_match']} (conf={res['confidence']:.2f})")
            combined_rows.append([base, v["name"], res.get("best_match",""), float(res.get("confidence",0.0)), res.get("reason","")])

        with open(f"{base}_Mappings.json", "w", encoding="utf-8") as f:
            json.dump(mappings, f, indent=2)
        print(f"  Saved mappings → {base}_Mappings.json")

        # rename + provenance
        corrected = rename_with_conf(base, ttl, mappings, conf_thresh=CONF_THRESHOLD)

                # --- confidence-based flagging ---
        for res in mappings:
            conf = float(res.get("confidence", 0.0))
            if not res.get("best_match"):
                flag = "NO_MATCH"
                needs_human = True
            elif conf >= 0.6:
                flag = "HIGH_CONF"
                needs_human = False
            elif 0.4 <= conf < 0.6:
                flag = "LOW_CONF"
                needs_human = True
            else:
                flag = "NO_MATCH"
                needs_human = True
            res["confidence_flag"] = flag
            res["needs_human"] = needs_human


       # combined predictions with flags
    with open("combined_predictions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "base",
            "original",
            "best_match",
            "confidence",
            "confidence_flag",
            "needs_human",
            "reason"
        ])
        for m in combined_rows:
            # m = [base, original, best_match, conf, reason]
            base, orig, best, conf, reason = m
            if conf >= 0.7:
                flag, need_human = "HIGH_CONF", False
            elif 0.4 <= conf < 0.7:
                flag, need_human = "LOW_CONF", True
            elif not best:
                flag, need_human = "NO_MATCH", True
            else:
                flag, need_human = "NO_MATCH", True
            w.writerow([base, orig, best, conf, flag, need_human, reason])


if __name__ == "__main__":
    run_all()
