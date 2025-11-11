import json

file = "ONTOLOGY_FINAL.jsonld"
with open(file) as f:
    data = json.load(f)

def fix_ref(value):
    if isinstance(value, str):
        if value.startswith("xsd:"):
            return {"@id": value}
        if value[0].isupper() and not value.startswith("http"):
            return {"@id": f"https://example.org/ship/{value}"}
    return value

for item in data["@graph"]:
    if "rdfs:domain" in item:
        item["rdfs:domain"] = fix_ref(item["rdfs:domain"])
    if "rdfs:range" in item:
        item["rdfs:range"] = fix_ref(item["rdfs:range"])

with open("ONTOLOGY_FINAL_fixed.jsonld", "w") as f:
    json.dump(data, f, indent=2)
