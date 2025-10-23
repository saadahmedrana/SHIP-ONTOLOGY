# ===========================================================
# MASTER AGENT (EVAL MODE) — Safe read-only version
# Extract → Retrieve → Reason → Print results only
# ===========================================================

import os, re, json, time, glob
import numpy as np
import requests
from dotenv import load_dotenv
from rdflib import Graph, Namespace, RDF
import csv

# ---------------- CONFIG ----------------
load_dotenv()
AALTO_KEY = os.getenv("AALTO_KEY")
if not AALTO_KEY:
    raise EnvironmentError("Please set AALTO_KEY in your .env file.")

TTL_FILES = None               # None = auto-detect all OEM*_OEM.ttl
TOP_K = 5
SLEEP_BETWEEN_CALLS = 1.3      # seconds between each variable reasoning call
MAX_RETRIES = 2
BACKOFF = 8                   # seconds backoff on rate limit
SHOW_ONLY_SUMMARY = True       # prints summary at end
SHACL_RULES = None

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
fmu  = Namespace("http://example.com/fmu#")
ssn  = Namespace("http://www.w3.org/ns/ssn/")

# ---------------- UTILITIES ----------------
def embed_text_online(text, dim=3072):
    payload = {"input": text, "model": "text-embedding-3-large"}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.post(EMBED_URL, headers=HEADERS, json=payload, timeout=45)
            if r.status_code == 200:
                data = r.json()["data"][0]["embedding"]
                return np.array(data, dtype=np.float32)
            elif r.status_code == 429:
                print(f"⚠️  Rate limit hit, sleeping {BACKOFF}s (attempt {attempt})")
                time.sleep(BACKOFF)
                continue
            else:
                print(f"Embedding API error ({r.status_code}) — using zero-vector fallback.")
        except requests.exceptions.RequestException:
            print(f"Network issue (attempt {attempt}). Retrying...")
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

    return {"original": var, "best_match": "", "confidence": 0.0, "reason": "max retries exceeded"}


# ---------------- MAIN ----------------
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
            vars_list.append({"id": str(s), "name": name})

        print(f"  Extracted {len(vars_list)} vars")

        # inside run_eval(), when iterating variables:
        for v in vars_list:
            query = f"Variable '{v['name']}' from OEM dataset"
            vec = embed_text_online(query, dim)
            sims = cosine_similarity(vec, onto_vecs)
            idx = np.argsort(sims)[::-1][:TOP_K]
            tops = [{"id": onto_ids[i], "similarity": float(sims[i]), "text": onto_txts[i]} for i in idx]
            res = reason_best_match(v["name"], query, tops)

            # ⬇️ include the file/base NOW
            results.append({
                "file": base,                  # e.g., OEMA_OEM
                "original_name": v["name"],
                "best_match": res.get("best_match",""),
                "confidence": float(res.get("confidence", 0.0)),
                "reason": res.get("reason","")
            })

            print(f"  → {v['name']} → {res['best_match']} (conf={res['confidence']:.2f})")
            time.sleep(SLEEP_BETWEEN_CALLS)

        # then write CSV exactly from results:
        with open("eval_results.csv", "w", newline="", encoding="utf-8") as f:
            import csv
            w = csv.DictWriter(f, fieldnames=["file","original_name","best_match","confidence","reason"])
            w.writeheader()
            w.writerows(results)
        print("✅ Saved results → eval_results.csv")
    print("\n📊 === SUMMARY ===")
    total = len(results)
    high = sum(1 for r in results if r["confidence"] >= 0.7)
    low = sum(1 for r in results if 0.4 <= r["confidence"] < 0.7)
    none = sum(1 for r in results if r["confidence"] < 0.4)
    print(f" Total variables: {total}")
    print(f" High confidence (≥0.7): {high}")
    print(f" Low confidence (0.4–0.7): {low}")
    print(f" No match (<0.4): {none}")

    print("\nExample outputs:")
    for r in results[:5]:
        print(json.dumps(r, indent=2))


if __name__ == "__main__":
    run_eval()
