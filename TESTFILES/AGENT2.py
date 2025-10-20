# -----------------------------------------------------------
# AGENT 2 — REASONER  (Aalto OpenAI version)
# Chooses the best canonical ontology match using GPT-4.1-2025-04-14
# -----------------------------------------------------------

import os
import json
import requests
from dotenv import load_dotenv

# ---------- CONFIG ----------
load_dotenv()
AALTO_KEY = os.getenv("AALTO_KEY")
if not AALTO_KEY:
    raise EnvironmentError("⚠️  Please set AALTO_KEY in your .env file.")

INPUT  = "TopMatches_Engine_Test1.json"
OUTPUT = "Mapping_Results_Engine_Test1.json"

# ✅ use latest Aalto deployment endpoint
LLM_URL = "https://aalto-openai-apigw.azure-api.net/v1/openai/deployments/gpt-4.1-2025-04-14/chat/completions"
MODEL   = "gpt-4.1-2025-04-14"

HEADERS = {
    "Content-Type": "application/json",
    "Ocp-Apim-Subscription-Key": AALTO_KEY
}


# ---------- MAIN ----------
def main():
    with open(INPUT, "r", encoding="utf-8") as f:
        candidates_data = json.load(f)

    results = []

    for entry in candidates_data:
        var = entry["original_variable"]
        query = entry["query_text"]
        top_matches = entry["top_matches"]

        prompt = f"""
You are a reasoning agent for ontology variable mapping in maritime engineering.

OEM variable to analyze:
{query}

Top ontology candidates (with similarity):
{json.dumps(top_matches, indent=2)}

Choose the SINGLE most appropriate canonical ontology variable ID.
Respond ONLY in this JSON format:
{{
  "original": "{var}",
  "best_match": "<ontology_id>",
  "confidence": <0.0-1.0>,
  "reason": "<short explanation>"
}}
"""

        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "You are a precise ontology reasoning assistant."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }

        print(f"\n🧠 Reasoning for variable: {var}")
        r = requests.post(LLM_URL, headers=HEADERS, json=payload, timeout=90)

        if r.status_code != 200:
            print(f"⚠️  API Error ({r.status_code}): {r.text[:300]}")
            continue

        try:
            content = r.json()["choices"][0]["message"]["content"]
            result = json.loads(content)
            print(f"✅ Best match: {result['best_match']} (conf {result['confidence']:.2f})")
            results.append(result)
        except Exception as e:
            print("❌ Parsing error:", e)
            print("Raw response:\n", r.text[:400])

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Reasoning complete → {OUTPUT}")


if __name__ == "__main__":
    main()
