#!/usr/bin/env python3

from rdflib import Graph
from pathlib import Path
from collections import defaultdict
import csv
import json

# ---------------- CONFIG ----------------
OUT_DIR = Path(".")
CSV_PER_FILE = OUT_DIR / "oem_variables_per_file.csv"
CSV_UNIQUE = OUT_DIR / "oem_variables_unique.csv"
JSON_ALL = OUT_DIR / "oem_variables_all.json"

# SPARQL query: ONLY OEM variable names
QUERY = """
PREFIX fmu: <http://example.com/fmu#>
PREFIX ssp: <http://example.com/ssp#>

SELECT DISTINCT ?varName
WHERE {
  { ?v fmu:hasFMUVariableName ?varName }
  UNION
  { ?v ssp:hasVariableName ?varName }
}
"""

def extract_from_ttl(ttl_path: Path):
    g = Graph()
    g.parse(ttl_path, format="turtle")
    return sorted(str(row.varName) for row in g.query(QUERY))


def main():
    ttl_files = sorted(Path(".").glob("*.ttl"))

    if not ttl_files:
        print("❌ No .ttl files found in this directory")
        return

    all_vars = set()
    per_file = defaultdict(list)

    for ttl in ttl_files:
        try:
            vars_ = extract_from_ttl(ttl)
            if vars_:
                per_file[ttl.name] = vars_
                all_vars.update(vars_)
        except Exception as e:
            print(f"⚠️ Failed to parse {ttl.name}: {e}")

    # ---------------- TERMINAL OUTPUT ----------------
    print("\n==============================")
    print("PER-FILE VARIABLE NAMES")
    print("==============================")

    for fname, vars_ in per_file.items():
        print(f"\n# {fname}  ({len(vars_)} vars)")
        for v in vars_:
            print(v)

    print("\n==============================")
    print(f"TOTAL UNIQUE VARIABLES: {len(all_vars)}")
    print("==============================")

    for v in sorted(all_vars):
        print(v)

    # ---------------- CSV: per file ----------------
    with open(CSV_PER_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["variable_name", "source_file"])
        for fname, vars_ in per_file.items():
            for v in vars_:
                writer.writerow([v, fname])

    # ---------------- CSV: unique ----------------
    with open(CSV_UNIQUE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["variable_name"])
        for v in sorted(all_vars):
            writer.writerow([v])

    # ---------------- JSON (optional but useful) ----------------
    with open(JSON_ALL, "w", encoding="utf-8") as f:
        json.dump(
            {
                "per_file": per_file,
                "unique_variables": sorted(all_vars)
            },
            f,
            indent=2
        )

    print("\n✅ Files written:")
    print(f"  - {CSV_PER_FILE}")
    print(f"  - {CSV_UNIQUE}")
    print(f"  - {JSON_ALL}")


if __name__ == "__main__":
    main()
