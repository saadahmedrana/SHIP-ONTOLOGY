from rdflib import Graph

# Path to your ontology JSON-LD
ONTOLOGY_FILE = "ONTOLOGY_FINAL.jsonld"

# Create an RDF graph
g = Graph()

# Parse JSON-LD into RDF triples
g.parse(ONTOLOGY_FILE, format="json-ld")

print(f" Loaded {len(g)} RDF triples from {ONTOLOGY_FILE}\n")

# Show a few triples
for s, p, o in list(g)[:10]:
    print(s, p, o)

# Optionally export to TTL for inspection
g.serialize(destination="ONTOLOGY_FINAL.ttl", format="turtle")
print("\n Saved RDF triples to ONTOLOGY_FINAL.ttl")
