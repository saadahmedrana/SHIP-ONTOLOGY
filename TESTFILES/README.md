# OEM Synthetic Dataset

- **Count**: 12 OEM files, 101 total variables (8–9 per file).
- **Purpose**: Stress-test extraction → retrieval → reasoning by providing OEM-style variable names with rich context and correct ground-truth mappings.
- **How to use**:
  1. Run your pipeline on each `*_OEM.ttl` to produce predicted mappings.
  2. Compare with `master_mapping.csv` (`original_name` → `canonical_id`) to score accuracy.
- **Notes**:
  - Files use `fmu:hasFMUVariableName` + `sosa:ObservableProperty` + `sosa:Observation` for realistic context.
  - No canonical identifiers appear in OEM files (ground truth only in CSV).
