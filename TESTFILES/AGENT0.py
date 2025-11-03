# -----------------------------------------------------------
# VARIABLE EXTRACTION AGENT (Agent_0)
# Reads an OEM .ttl file and outputs a JSON list of variables
# -----------------------------------------------------------d----

import json
from rdflib import Graph, Namespace, RDF

# --- user settings ---
input_file = "Engine_Test1.ttl"
output_file = "Variables_Engine_Test1.json"

# --- namespaces (add more if needed) ---
sosa = Namespace("http://www.w3.org/ns/sosa/")
ssn  = Namespace("http://www.w3.org/ns/ssn/")
fmu  = Namespace("http://example.com/fmu#")
ssp  = Namespace("http://example.com/ssp#")
qudt = Namespace("http://qudt.org/2.1/schema/qudt#")

# --- load graph ---
g = Graph()
g.parse(input_file, format="turtle")

records = []

for subj, _, _ in g.triples((None, RDF.type, None)):
    # consider variables only
    if (subj, RDF.type, sosa.ObservableProperty) in g or (subj, RDF.type, ssn.Property) in g:
        rid = str(subj)
        # collect info
        name = None
        context = None
        dtype = None
        unit = None
        value = None

        for _, _, o in g.triples((subj, fmu.hasFMUVariableName, None)):
            name = str(o)
        for _, _, o in g.triples((subj, ssp.hasVariableName, None)):
            name = str(o)
        for _, _, o in g.triples((subj, ssn.isPropertyOf, None)):
            context = str(o)
        for _, _, o in g.triples((subj, fmu.hasDataType, None)):
            dtype = str(o)
        for _, _, o in g.triples((subj, ssp.hasDataType, None)):
            dtype = str(o)
        for _, _, o in g.triples((subj, qudt.unit, None)):
            unit = str(o)
        # look for observation value
        for obs, _, _ in g.triples((None, sosa.observedProperty, subj)):
            for _, _, val in g.triples((obs, sosa.hasSimpleResult, None)):
                value = str(val)

        rec = {
            "id": rid,
            "name": name,
            "context": context,
            "datatype": dtype,
            "unit": unit,
            "value": float(value) if value else None
        }
        records.append(rec)

# --- write output ---
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(records, f, indent=2)

print(f"Extracted {len(records)} variable(s) → {output_file}")
