# -----------------------------------------------------------
# PIPELINE ORCHESTRATOR — Extract → Retrieve → Reason (Aalto)
# One command for many variables in one OEM .ttl file
# -----------------------------------------------------------
# Requires: rdflib, numpy, requests, python-dotenv
# Files needed in working dir:
#   - ontology_vectors.npy
#   - ontology_ids.json
#   - ontology_texts.json
#
# Usage:
#   python pipeline_orchestrator.py --ttl EngineTEST.ttl --k 5
#
# Outputs (for the given TTL basename, e.g., EngineTEST):
#   - EngineTEST_Variables.json            (extracted variables)
#   - EngineTEST_TopMatches.json           (retrieval results)
#   - EngineTEST_Mappings.json             (reasoner decisions)
#   - EngineTEST_Mappings.csv              (compact table)
# -----------------------------------------------------------

import os, re, json, time, argparse, csv
import numpy as np
import requests
from dotenv import load_dotenv

from rdflib import Graph, Namespace, RDF

# ---------- ENV / CONFIG ----------
load_dotenv()
AALTO_KEY = os.getenv("AALTO_KEY")
if not AALTO_KEY:
    raise EnvironmentError("⚠️  Please set AALTO_KEY in your .env file.")

EMBED_MODEL = "text-embedding-3-large"
EMBED_URL   = "https://aalto-openai-apigw.azure-api.net/v1/openai/text-embedding-3-large/embeddings"
LLM_URL     = "https://aalto-openai-apigw.azure-api.net/v1/openai/deployments/gpt-4.1-2025-04-14/chat/completions"
LLM_MODEL   = "gpt-4.1-2025-04-14"

HEADERS = {"Content-Type": "application/json", "Ocp-Apim-Subscription-Key": AALTO_KEY}

# ontology store (precomputed)
ONTO_VECS = "ontology_vectors.npy"
ONTO_IDS  = "ontology_ids.json"
ONTO_TXTS = "ontology_texts.json"

# Namespaces (same as AGENT0)
sosa = Namespace("http://www.w3.org/ns/sosa/")
ssn  = Namespace("http://www.w3.org/ns/ssn/")
fmu  = Namespace("http://example.com/fmu#")
ssp  = Namespace("http://example.com/ssp#")
qudt = Namespace("http://qudt.org/2.1/schema/qudt#")

# ---------- UTILITIES ----------
def qudt_uri_to_label(u: str) -> str:
    if not u:
        return ""
    # Accept both plain CURIEs and full URIs
    txt = str(u)
    # Common readable fallbacks
    mapping = {
        "unit:KiloW": "kilowatts (kW)",
        "unit:REV-PER-SEC": "revolutions per second (1/s)",
        "unit:REV-PER-MIN": "revolutions per minute (rpm)",
        "unit:KiloN-M": "kiloNewton-meters (kNm)",
        "unit:KiloN": "kiloNewtons (kN)",
        "unit:M3": "cubic meters (m³)",
        "unit:MPa": "megapascals (MPa)",
        "unit:DEG": "degrees (deg)",
        "unit:M": "meters (m)",
        "unit:MM": "millimeters (mm)",
        "unit:Knot": "knots (kn)",
        "unit:HZ": "hertz (Hz)",
    }
    # Try CURIE match first
    for k, v in mapping.items():
        if k in txt:
            return v
    # Otherwise try to take last path fragment as a readable token
    frag = re.split(r"[#/]", txt.strip())
    last = frag[-1] if frag else txt
    return last

def embed_text_online(text: str, retries: int = 3, sleep=5):
    payload = {"input": text, "model": EMBED_MODEL}
    for attempt in range(1, retries + 1):
        try:
            r = requests.post(EMBED_URL, headers=HEADERS, json=payload, timeout=30)
            if r.status_code == 200:
                emb = r.json()["data"][0]["embedding"]
                return np.array(emb, dtype=np.float32)
            else:
                print(f"⚠️  Embedding API error ({r.status_code}): {r.text[:200]}")
        except requests.exceptions.RequestException:
            print(f"❌ Embedding conn attempt {attempt} failed — VPN/network?")
        if attempt < retries:
            print(f"⏳ Retrying in {sleep}s...")
            time.sleep(sleep)
    print("🚨 Embedding API unreachable. Using zero-vector fallback (results unreliable).")
    return np.zeros(3072, dtype=np.float32)

def cosine_similarity(vec, mat):
    if np.linalg.norm(vec) == 0:
        return np.zeros(mat.shape[0])
    v = vec / np.linalg.norm(vec)
    M = mat / np.linalg.norm(mat, axis=1, keepdims=True)
    return M @ v

def build_query_text(v):
    """Richer text to give the embedder semantic signal."""
    name  = v.get("name") or ""
    ctx   = v.get("context") or ""
    unit  = qudt_uri_to_label(v.get("unit") or "")
    dtype = v.get("datatype") or ""
    val   = v.get("value")
    approx = f"{val}" if val is not None else "unknown"

    # lightweight heuristics based on common engineering abbreviations
    hints = []
    low = name.lower()
    if re.search(r"\bp[_\-]?(w|me)?\b", low) or low in ("p", "p_w", "p_me", "engine_power"):
        hints.append("This likely denotes engine POWER.")
    if "omega" in low or "n_rpm" in low or "rpm" in low or "rev" in low:
        hints.append("This likely denotes ROTATIONAL SPEED.")
    if low.startswith("t") or "torq" in low:
        hints.append("This likely denotes TORQUE.")
    if "bollard" in low:
        hints.append("This may denote BOLLARD THRUST.")
    if "ychest" in low or "seachest" in low:
        hints.append("This may denote SEA CHEST VOLUME for cooling water.")
    if "y_strength" in low or "yield" in low:
        hints.append("This likely denotes MATERIAL YIELD STRENGTH (MPa).")

    hint_txt = " ".join(hints)

    return (
        "This is an OEM variable from a marine powertrain dataset. "
        f"Variable name: '{name}'. "
        f"Unit: {unit if unit else 'unspecified'}. "
        f"Context system IRI: {ctx}. "
        f"Datatype: {dtype}. "
        f"Observed value (approx): {approx}. "
        f"{hint_txt} "
        "Find the single best canonical ontology property (ID) with the same physical meaning and unit."
    )

def reason_best_match(var_name, query_text, top_matches):
    """Call Aalto GPT-4.1 to choose best ontology ID."""
    # few-shot helps a lot
    examples = """
Guidelines for reasoning:
- Expand common abbreviations (P → Power, T → Torque, n/omega → Rotational speed).
- Match variables to ontology properties that describe the same physical quantity and share consistent units.
- Consider engineering domains: engine, propulsion, hull, or materials.
- If none of the candidates represent the same concept, set best_match="" and confidence=0.0.
"""

    prompt = f"""
You are a neutral ontology reasoning agent for maritime engineering.

OEM variable (with metadata):
{query_text}

Top ontology candidates (id, similarity, text):
{json.dumps(top_matches, indent=2)}

{examples}

Rules:
- Always pick exactly one ontology ID from the candidates if any match meaning+unit+domain best.
- If none is appropriate, set best_match="" and confidence=0.0.
- Respond ONLY in this JSON (no prose):
{{
  "original": "{var_name}",
  "best_match": "<ontology_id or empty>",
  "confidence": <0.0-1.0>,
  "reason": "<very short>"
}}
"""

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "You are a precise ontology reasoning assistant. Output strict JSON only."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    r = requests.post(LLM_URL, headers=HEADERS, json=payload, timeout=120)
    if r.status_code != 200:
        return {"original": var_name, "best_match": "", "confidence": 0.0,
                "reason": f"LLM API error {r.status_code}: {r.text[:200]}"}
    try:
        content = r.json()["choices"][0]["message"]["content"].strip()
        # try to extract strict JSON
        start = content.find("{")
        end   = content.rfind("}") + 1
        parsed = json.loads(content[start:end])
        # sanity
        parsed.setdefault("original", var_name)
        parsed.setdefault("best_match", "")
        parsed.setdefault("confidence", 0.0)
        parsed.setdefault("reason", "")
        return parsed
    except Exception as e:
        return {"original": var_name, "best_match": "", "confidence": 0.0,
                "reason": f"Parse error: {e}. Raw: {content[:200]}"}

def extract_variables_from_ttl(ttl_path):
    g = Graph()
    g.parse(ttl_path, format="turtle")
    vars_out = []

    for subj, _, _ in g.triples((None, RDF.type, None)):
        if (subj, RDF.type, sosa.ObservableProperty) in g or (subj, RDF.type, ssn.Property) in g:
            rid = str(subj)
            name = None; ctx=None; dtype=None; unit_uri=None; val=None
            for _, _, o in g.triples((subj, fmu.hasFMUVariableName, None)):
                name = str(o)
            for _, _, o in g.triples((subj, ssp.hasVariableName, None)):
                name = str(o)
            for _, _, o in g.triples((subj, ssn.isPropertyOf, None)):
                ctx = str(o)
            for _, _, o in g.triples((subj, fmu.hasDataType, None)):
                dtype = str(o)
            for _, _, o in g.triples((subj, ssp.hasDataType, None)):
                dtype = str(o)
            for _, _, o in g.triples((subj, qudt.unit, None)):
                unit_uri = str(o)
            # observation value (optional)
            for obs, _, _ in g.triples((None, sosa.observedProperty, subj)):
                for _, _, val_lit in g.triples((obs, sosa.hasSimpleResult, None)):
                    try:
                        val = float(str(val_lit))
                    except:
                        val = str(val_lit)

            vars_out.append({
                "id": rid, "name": name, "context": ctx, "datatype": dtype,
                "unit": unit_uri, "value": val
            })
    return vars_out

def run_pipeline(ttl_path, top_k):
    # load ontology store
    onto_vecs = np.load(ONTO_VECS)
    onto_ids  = json.load(open(ONTO_IDS, "r", encoding="utf-8"))
    onto_txts = json.load(open(ONTO_TXTS, "r", encoding="utf-8"))

    base = os.path.splitext(os.path.basename(ttl_path))[0]
    out_vars   = f"{base}_Variables.json"
    out_top    = f"{base}_TopMatches.json"
    out_map    = f"{base}_Mappings.json"
    out_csv    = f"{base}_Mappings.csv"

    # 1) Extract
    print(f"📥 Extracting variables from {ttl_path} ...")
    variables = extract_variables_from_ttl(ttl_path)
    with open(out_vars, "w", encoding="utf-8") as f:
        json.dump(variables, f, indent=2)
    print(f"✅ Extracted {len(variables)} vars → {out_vars}")

    # 2) Retrieve
    print("🔎 Running retrieval via online embeddings ...")
    all_tops = []
    for v in variables:
        qtext = build_query_text(v)
        qvec  = embed_text_online(qtext)
        sims  = cosine_similarity(qvec, onto_vecs)
        idx   = np.argsort(sims)[::-1][:top_k]
        top_matches = [{"id": onto_ids[i], "similarity": float(sims[i]), "text": onto_txts[i]} for i in idx]
        all_tops.append({"original_variable": v.get("name"), "query_text": qtext, "top_matches": top_matches})
        print(f"  • {v.get('name')}: best ~ {top_matches[0]['id']} (sim {top_matches[0]['similarity']:.3f})")

    with open(out_top, "w", encoding="utf-8") as f:
        json.dump(all_tops, f, indent=2)
    print(f"✅ Saved top matches → {out_top}")

    # 3) Reason
    print("🧠 Calling LLM reasoner for each variable ...")
    mappings = []
    for item in all_tops:
        var = item["original_variable"]
        res = reason_best_match(var, item["query_text"], item["top_matches"])
        mappings.append(res)
        print(f"  • {var} → {res['best_match']} (conf {res['confidence']:.2f})")

    with open(out_map, "w", encoding="utf-8") as f:
        json.dump(mappings, f, indent=2)
    print(f"✅ Saved mappings → {out_map}")

    # 4) CSV summary
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["original", "best_match", "confidence", "reason"])
        for m in mappings:
            w.writerow([m.get("original",""), m.get("best_match",""), m.get("confidence",0.0), m.get("reason","")])
    print(f"📄 Summary table → {out_csv}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ttl", required=True, help="Path to OEM .ttl file")
    ap.add_argument("--k", type=int, default=5, help="Top-K candidates for retrieval")
    args = ap.parse_args()
    run_pipeline(args.ttl, args.k)

if __name__ == "__main__":
    main()