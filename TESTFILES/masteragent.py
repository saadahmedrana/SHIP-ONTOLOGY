# ===========================================================
# MASTER AGENT — Full Automated Pipeline
# Extract → Retrieve → Reason → Rename → Validate (SHACL)
# ===========================================================

import os, re, json, time, csv, numpy as np, requests
from dotenv import load_dotenv
from rdflib import Graph, Namespace, RDF, OWL, URIRef, Literal
from rdflib.namespace import PROV, XSD
from pyshacl import validate   # <- make sure pyshacl is installed

# ---------------- CONFIG ----------------
load_dotenv()
AALTO_KEY = os.getenv("AALTO_KEY")
if not AALTO_KEY:
    raise EnvironmentError(" Please set AALTO_KEY in your .env file!!!!")

# --- user-definable section ---
TTL_FILES = ["Engine_Test1.ttl"]     # list of OEM ttl files to process
TOP_K = 5                            # retrieval depth
CONF_THRESHOLD = 0.4                 # auto-accept confidence for renaming
SHACL_RULES = "TRAFICOM_SHACL.ttl"   # your SHACL file (placeholder)

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
def embed_text_online(text):
    payload = {"input": text, "model": "text-embedding-3-large"}
    r = requests.post(EMBED_URL, headers=HEADERS, json=payload, timeout=45)
    if r.status_code == 200:
        return np.array(r.json()["data"][0]["embedding"], dtype=np.float32)
    print(f"  Embedding API error ({r.status_code}) — using zero vector.")
    return np.zeros(3072, dtype=np.float32)

def cosine_similarity(vec, mat):
    if np.linalg.norm(vec) == 0:
        return np.zeros(mat.shape[0])
    v = vec / np.linalg.norm(vec)
    M = mat / np.linalg.norm(mat, axis=1, keepdims=True)
    return M @ v

def qudt_uri_to_label(u: str):
    if not u: return ""
    txt = str(u)
    for k,v in {"unit:KiloW":"kW","unit:KiloN-M":"kNm","unit:REV-PER-MIN":"rpm","unit:M3":"m³","unit:MPa":"MPa"}.items():
        if k in txt: return v
    return txt.split("#")[-1]

def reason_best_match(var, query_text, top_matches):
    prompt = f"""
You are a reasoning agent mapping OEM variables to ontology concepts.
Variable metadata:
{query_text}

Candidates:
{json.dumps(top_matches, indent=2)}

Guidelines:
- Expand abbreviations (P→Power, T→Torque, omega/n→Speed).
- Choose exactly one ID that best matches meaning+unit+domain.
- If uncertain, leave best_match empty.

Return strict JSON:
{{
  "original":"{var}",
  "best_match":"<ontology_id or empty>",
  "confidence":<0.0-1.0>,
  "reason":"<short>"
}}
"""
    payload = {
        "model":"gpt-4.1-2025-04-14",
        "messages":[{"role":"system","content":"Output only valid JSON."},
                    {"role":"user","content":prompt}],
        "temperature":0.1
    }
    r = requests.post(LLM_URL, headers=HEADERS, json=payload, timeout=120)
    if r.status_code != 200:
        return {"original":var,"best_match":"","confidence":0.0,"reason":"API error"}
    try:
        content = r.json()["choices"][0]["message"]["content"]
        start, end = content.find("{"), content.rfind("}")+1
        return json.loads(content[start:end])
    except Exception:
        return {"original":var,"best_match":"","confidence":0.0,"reason":"parse error"}

# ---------------- PIPELINE STEPS ----------------
def extract_vars(ttl):
    g = Graph(); g.parse(ttl, format="turtle")
    vars=[]
    for s,_p,_o in g.triples((None,RDF.type,None)):
        if (s,RDF.type,sosa.ObservableProperty) in g or (s,RDF.type,ssn.Property) in g:
            rec={"id":str(s),"name":None,"context":None,"datatype":None,"unit":None,"value":None}
            for _,_,o in g.triples((s,fmu.hasFMUVariableName,None)): rec["name"]=str(o)
            for _,_,o in g.triples((s,ssn.isPropertyOf,None)): rec["context"]=str(o)
            for _,_,o in g.triples((s,fmu.hasDataType,None)): rec["datatype"]=str(o)
            for _,_,o in g.triples((s,qudt.unit,None)): rec["unit"]=str(o)
            for obs,_,_ in g.triples((None,sosa.observedProperty,s)):
                for _,_,val in g.triples((obs,sosa.hasSimpleResult,None)): rec["value"]=float(val)
            vars.append(rec)
    return vars

def build_query(v):
    return f"Var '{v['name']}', Unit: {qudt_uri_to_label(v['unit'])}, Context: {v['context']}, Value: {v['value']}"

def rename_with_conf(base, ttl_file, mappings):
    out_file = f"{base}_corrected.ttl"
    g = Graph(); g.parse(ttl_file, format="turtle")
    changes=0; low_conf=[]
    for m in mappings:
        orig,best,conf = m.get("original"), m.get("best_match"), m.get("confidence",0.0)
        if not best: continue
        if conf < CONF_THRESHOLD:
            low_conf.append(m); continue
        for subj,_,val in g.triples((None,fmu.hasFMUVariableName,None)):
            if str(val)==orig:
                old=subj; new=URIRef(best)
                g.add((old,owl.sameAs,new))
                g.add((old, prov.confidence, Literal(conf, datatype=XSD.decimal)))

                changes+=1
    g.serialize(out_file,format="turtle")
    print(f" Applied {changes} confident renames → {out_file}")
    if low_conf:
        json.dump(low_conf,open(f"{base}_LowConfidence.json","w"),indent=2)
        print(f"  {len(low_conf)} low-confidence mappings saved for review.")
    return out_file

def validate_with_shacl(data_file, shacl_file):
    if not os.path.exists(shacl_file):
        print(f" SHACL file '{shacl_file}' not found — skipping validation.")
        return
    conforms, results_graph, text = validate(
        data_graph=data_file, shacl_graph=shacl_file,
        inference='rdfs', serialize_report_graph=True)
    print("🔍 SHACL validation results:")
    print(text)
    with open(f"{os.path.splitext(data_file)[0]}_SHACL_Report.ttl","wb") as f:
        f.write(results_graph)
    return conforms

# ---------------- MAIN ----------------
def run_all():
    onto_vecs=np.load(ONTO_VECS)
    onto_ids=json.load(open(ONTO_IDS))
    onto_txts=json.load(open(ONTO_TXTS))

    for ttl in TTL_FILES:
        base=os.path.splitext(os.path.basename(ttl))[0]
        print(f"\n=================  Processing {ttl} =================")
        vars=extract_vars(ttl)
        print(f" Extracted {len(vars)} vars")

        # retrieval + reasoning
        mappings=[]
        for v in vars:
            q=build_query(v)
            vec=embed_text_online(q)
            sims=cosine_similarity(vec,onto_vecs)
            top_idx=np.argsort(sims)[::-1][:TOP_K]
            tops=[{"id":onto_ids[i],"similarity":float(sims[i]),"text":onto_txts[i]} for i in top_idx]
            res=reason_best_match(v["name"],q,tops)
            mappings.append(res)
            print(f"  → {v['name']} → {res['best_match']} (conf={res['confidence']:.2f})")

        json.dump(mappings,open(f"{base}_Mappings.json","w"),indent=2)
        print(f" Saved mappings → {base}_Mappings.json")

        # rename + provenance
        corrected=rename_with_conf(base,ttl,mappings)

        # SHACL validation
        validate_with_shacl(corrected,SHACL_RULES)

if __name__=="__main__":
    run_all()
