# -----------------------------------------------------------
# AGENT 1 — RETRIEVER (v2)
# Finds top-k ontology matches for OEM variables
# Generates new embeddings online for OEM queries (Aalto API)
# -----------------------------------------------------------

import os
import json
import time
import numpy as np
import requests
from dotenv import load_dotenv

# ---------- CONFIG ----------
load_dotenv()
AALTO_KEY = os.getenv("AALTO_KEY")
if not AALTO_KEY:
    raise EnvironmentError("⚠️  Please set AALTO_KEY in your .env file.")

ONTO_VECS = "ontology_vectors.npy"
ONTO_IDS  = "ontology_ids.json"
ONTO_TXTS = "ontology_texts.json"
OEM_VARS  = "Variables_Engine_Test1.json"
OUTPUT    = "TopMatches_Engine_Test1.json"

EMBED_MODEL = "text-embedding-3-large"
EMBED_URL   = "https://aalto-openai-apigw.azure-api.net/v1/openai/text-embedding-3-large/embeddings"
HEADERS     = {"Content-Type": "application/json", "Ocp-Apim-Subscription-Key": AALTO_KEY}
TOP_K = 5


# ---------- FUNCTIONS ----------
def embed_text_online(text: str, retries: int = 3):
    """Call Aalto embedding API with retries and VPN check."""
    payload = {"input": text, "model": EMBED_MODEL}

    for attempt in range(1, retries + 1):
        try:
            r = requests.post(EMBED_URL, headers=HEADERS, json=payload, timeout=20)
            if r.status_code == 200:
                data = r.json()["data"][0]["embedding"]
                print(f"🧩 Received embedding ({len(data)} dims)")
                return np.array(data, dtype=np.float32)
            else:
                print(f"⚠️  API error ({r.status_code}): {r.text[:200]}")
        except requests.exceptions.RequestException:
            print(f"❌ Connection attempt {attempt} failed — check VPN or network...")

        if attempt < retries:
            print("⏳ Retrying in 5 seconds...")
            time.sleep(5)

    # Fallback
    print("🚨 Could not reach Aalto API after multiple tries. Please turn on VPN.")
    print("⚙️  Using fallback zero-vector (retrieval accuracy will be invalid).")
    return np.zeros(3072, dtype=np.float32)  # same size as text-embedding-3-large output


def cosine_similarity(vec, mat):
    """Compute cosine similarity between one vector and a matrix."""
    if np.linalg.norm(vec) == 0:
        return np.zeros(mat.shape[0])
    vec_norm = vec / np.linalg.norm(vec)
    mat_norm = mat / np.linalg.norm(mat, axis=1, keepdims=True)
    return np.dot(mat_norm, vec_norm)


# ---------- MAIN ----------
def main():
    print("🧠 Loading ontology embeddings ...")
    onto_vecs = np.load(ONTO_VECS)
    onto_ids  = json.load(open(ONTO_IDS, "r", encoding="utf-8"))
    onto_txts = json.load(open(ONTO_TXTS, "r", encoding="utf-8"))

    print("📥 Loading OEM variables ...")
    variables = json.load(open(OEM_VARS, "r", encoding="utf-8"))

    results = []

    for v in variables:
        name = v.get("name", "")
        unit = v.get("unit", "")
        ctx  = v.get("context", "")
        dtype = v.get("datatype", "")
        val  = v.get("value", "")

        query_text = f"Variable: {name}. Unit: {unit}. Context: {ctx}. Datatype: {dtype}. Value: {val}."
        print(f"\n🔍 Embedding query for variable: {name}")

        # --- ONLINE EMBEDDING CALL ---
        q_emb = embed_text_online(query_text)

        # --- SIMILARITY CALCULATION ---
        sims = cosine_similarity(q_emb, onto_vecs)
        top_idx = np.argsort(sims)[::-1][:TOP_K]

        top_matches = []
        for i in top_idx:
            top_matches.append({
                "id": onto_ids[i],
                "similarity": float(sims[i]),
                "text": onto_txts[i]
            })

        results.append({
            "original_variable": name,
            "query_text": query_text,
            "top_matches": top_matches
        })

    # --- SAVE OUTPUT ---
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n✅ Retrieval complete → {OUTPUT}")


if __name__ == "__main__":
    main()
