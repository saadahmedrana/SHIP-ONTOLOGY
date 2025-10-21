# -----------------------------------------------------------
# AGENT 3 — RENAMER
# Rewrites OEM .ttl with canonical ontology variable names
# -----------------------------------------------------------

import os
import json
from rdflib import Graph, Namespace, RDF, OWL, URIRef, Literal
from rdflib.namespace import PROV, XSD

# --- user settings ---
# --- user settings ---
OEM_FILE = "./Engine_Test1.ttl"                # ✅ correct file name
MAPPINGS_FILE = "./Engine_Test1_Mappings.json" # ✅ your existing mappings file
OUTPUT_FILE = "./Engine_Test1_corrected.ttl"   # ✅ corrected output


# --- namespaces ---
sosa = Namespace("http://www.w3.org/ns/sosa/")
ssn  = Namespace("http://www.w3.org/ns/ssn/")
fmu  = Namespace("http://example.com/fmu#")
prov = Namespace("http://www.w3.org/ns/prov#")
owl  = OWL

# --- load OEM graph ---
print(f"📥 Loading OEM file: {OEM_FILE}")
g = Graph()
g.parse(OEM_FILE, format="turtle")
print(f"Parsed {len(g)} triples")

# --- load mappings ---
with open(MAPPINGS_FILE, "r", encoding="utf-8") as f:
    mappings = json.load(f)

print(f"Loaded {len(mappings)} mappings")

# --- apply renamings ---
changes = 0
for m in mappings:
    orig_name = m.get("original")
    best_match = m.get("best_match")
    conf = m.get("confidence", 0.0)

    if not best_match or conf < 0.3:  # ignore low confidence
        continue

    # Find all subjects whose fmu:hasFMUVariableName equals this OEM name
    for subj, _, val in g.triples((None, fmu.hasFMUVariableName, None)):
        if str(val).strip() == orig_name.strip():
            old_uri = subj
            new_uri = URIRef(best_match)

            # 1️⃣ Add provenance links
            g.add((old_uri, owl.sameAs, new_uri))
            g.add((old_uri, prov.confidence, Literal(conf, datatype=XSD.decimal)))

            # 2️⃣ Optionally rename subject by adding triple and deleting old one
            # (RDF graphs are not mutable identifiers, but we can indicate new name)
            g.add((new_uri, RDF.type, sosa.ObservableProperty))
            g.add((new_uri, ssn.isPropertyOf, URIRef(str(m.get("context", "")))))
            print(f"🔁 {orig_name} → {best_match} (conf={conf:.2f})")
            changes += 1

print(f"✅ Applied {changes} renamings")

# --- write new file ---
g.serialize(OUTPUT_FILE, format="turtle")
print(f"💾 Corrected file saved → {OUTPUT_FILE}")
