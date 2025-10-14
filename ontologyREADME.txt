
# Ship Ontology — Usage Guide (A→E)

## 1) Purpose (why this ontology exists)

This ontology standardizes propulsion & powertrain terms so we can:

* **Model** engines, shafting, propulsors, thrusters, and their materials/monitoring context.
* **Anchor** each data point to a TRAFICOM rule clause so compliance is machine-checkable.
* **Generate SHACL** shapes from structured “ConstraintIntent” items, and validate real ships.
* **Normalize messy data** (e.g., *Powerrrr* → canonical `mcrPower_kW`) using multi-agent mapping.

Phase E finished the cross-cutting layer (materials, monitoring & constraint anchors) as planned, so the ontology is now SHACL-ready. 

---

## 2) Overall structure (what’s in the graph)

### 2.1 Namespaces you’ll see

* `ship:, hull:, prop:, eng:, comp:, mat:, reg:` – domain
* `shacl:, shape:` – SHACL vocabulary & your shape graph
* QUDT & unit terms present from earlier phases (used sparsely, keep xsd numbers for now)

### 2.2 Core modules (by responsibility)

* **PropulsionSystem hub** → links PrimeMover → TransmissionSystem → ShaftingSystem → PropulsorSystem; keeps `iceClass` and arrangement context. (Phase C) 
* **PrimeMover / Engine interface** → MCR power/speed, reversible, torque inputs for shaft methods. (Phase C) 
* **Transmission & Shafting** → ratio, stiffness, couplings, bearings, seals, brakes, torsional damping. (Phase C) 
* **Propulsors (Propeller / Nozzle / CP hub / Thruster)** → geometry, ice loads, fatigue/failure variables. (Phase D) 
* **Materials** → minimum strength/toughness and test metadata; links to components. (Phase E) 
* **Monitoring & Control** → sensors, events, logging, and required monitoring flags. (Phase E) 
* **Regulatory anchors** → `RegulatoryRequirementSet`, `ConstraintIntent`, and SHACL shapes. (Phase E) 

### 2.3 Propulsor details you can reference in rules

TRAFICOM Chapter 6 design loads are represented as properties (e.g., `Fb_kN`, `Ff_kN`, `Qsmax_kNm`, `Tb_kN`, `Tf_kN`, `Qmax_kNm`, blade failure `Fex_kN`, `Qsex_kNm`), plus operation factors (`k1, k2, k3`), immersion `h0`, ice block sizes `Hice/Hiced`, and fatigue counters `Nice/Nclass`. These terms map 1:1 to §6.5–6.6 headings so we can bind constraints later.

There’s also a helper class **`PropellerLoadSet`** with **`hasMember`** to group the six key loads for SHACL convenience. (Both the `@context` mapping and the property node exist.) 

---

## 3) What’s in `@context` that matters for rules

* All propulsion/propulsor variables from Phases C–D
* Phase E additions:

  * **Materials**: `yieldStrength_MPa`, `charpyV_J`, `elongation_percent`, test metadata, plus optional composite fields. 
  * **Monitoring**: `torsionalVibrationMonitoring`, `bladeLoadMonitoring`, sensor metadata (location, accuracy, rate). 
  * **Constraints**: `ConstraintIntent` fields (`hasRegulationClause`, `targetProperty`, `requiredValue`, `comparisonOperator`, `appliesWhen`, `severity`, `message`, `definedByRequirementSet`), and SHACL keys coerced to IRIs (`shacl:path`, `shacl:severity`, `shacl:targetClass`, `shacl:datatype`). 

---

## 4) How TRAFICOM is represented (anchors you can trust)

* **Design loads (§6.5)** → all named variables exist; see §6.5.1–6.5.4 & §6.5.3 torque pathways. 
* **Propeller design & shaft line (§6.6.2–§6.6.4)** → fatigue/failure terms, shaft checks, safety factors. 
* **Azimuthing thrusters (§6.6.5)** → ridge/impact loads (`Fti`, `Ftr`), vibration check flag. 
* **Rudder & steering (§5)** → design speed minima by ice class (IAS/IA/IB/IC). 
* **Materials (§6.4)** → elongation, Charpy V energy at −10 °C with exceptions per material. 

---

## 5) ConstraintIntents & SHACL (how rules are encoded)

### 5.1 ConstraintIntent (human-readable rule seed)

Each rule is a `ConstraintIntent` with:

* **what** (`targetProperty`)
* **how** (`comparisonOperator`, `requiredValue` or boolean)
* **when** (`appliesWhen`)
* **source clause** (`hasRegulationClause`) and **set** (`definedByRequirementSet`)
* **UX bits** (`severity`, `message`)

Examples already present:

* **Extreme yield ≥ 1.3** (`prop:safetyFactorExtremeYield`) → §6.6.4. 
* **CP hub bolts sized for Fex** (`prop:boltDesignForFex`) → §6.6.4. 
* **Rudder speed minima** (`prop:rudderDesignSpeed_kn`) → §5. 
* **Monitoring required for IA+** (`prop:torsionalVibrationMonitoring`) → §8. 

All of these are linked to **`reg:TRAFICOM_2021`** (`RegulatoryRequirementSet`). 

### 5.2 SHACL shapes (machine-enforced check)

We keep a master node shape `shape:TRAFICOMPhaseE` targeting `prop:PropulsionSystem` and several `PropertyShape`s. Today you have:

* `shape:safetyFactorExtremeYield` (minInclusive 1.3)
* `shape:boltDesignForFex` (hasValue true)
* `shape:rudderSpeedMinima` (placeholder; implement via SPARQL or per-class shapes)
  Plus a general `shacl:NodeShape` class node for clarity. 

> Tip: each shape has `rdfs:seeAlso` to its `ConstraintIntent` so tools can show the human rule next to the machine check. 

---

## 6) Typical rules you can define with what’s already modeled

Below is a non-exhaustive menu to copy from when you add more `ConstraintIntent`s / shapes:

**Propeller loads (§6.5)**

* Ensure `Fb_kN`, `Ff_kN`, `Qsmax_kNm`, `Tb_kN`, `Tf_kN`, `Qmax_kNm` present for the selected method (open vs ducted), and non-negative.
* Bind **method choice** to data completeness:
  “If `propellerType = ducted` ⇒ `throatDiameter_m`, `nozzleLength_m`, `lipThickness_mm` required.” 

**Blade failure (§6.5.4)**

* If CP hub → `boltDesignForFex = true` and `Fex_kN`/`Qsex_kNm` recorded. 

**Shaft line design (§6.5.3, §6.6.4)**

* Non-resonant: require `Qemax_kNm` and set design torque path.
* Resonant: if `resonanceWithin20pctOfMaxSpeed = true` ⇒ `analysisMethod` ∈ {timeDomain, frequencyDomain} AND result torques documented. (From Phase C plan acceptance.) 

**Thruster (§6.6.5)**

* Require `Fti_kN`, `Ftr_kN`, `Hr_m` and `globalVibrationCheck = true`. 

**Rudder (§5)**

* `rudderDesignSpeed_kn` ≥ class minimum (IAS 20, IA 18, IB 16, IC 14). 

**Materials (§6.4)**

* For seawater-exposed metals: `elongation_percent ≥ 15` AND (if not bronze/austenitic steel) `charpyV_J ≥ 20 @ −10 °C`; nodular cast iron ≥ 10 J @ −10 °C. (Modelled as ConstraintIntents with `appliesWhen materialKind = steel|…`.) 

**Monitoring (§8)**

* If `iceClass ≥ IA` ⇒ `torsionalVibrationMonitoring = true`; if ducted propeller ⇒ `bladeLoadMonitoring = true`. 

---

## 7) How to use each module when writing rules

* **Use `ConstraintIntent`** as your rule’s “source of truth”: set `targetProperty`, the required threshold or boolean, the clause URI, and an optional `appliesWhen` filter. 
* **Generate SHACL** (manual or scripted) from `ConstraintIntent`:

  * numeric bounds → `shacl:minInclusive`/`maxInclusive`
  * booleans → `shacl:hasValue true/false`
  * per-class thresholds (e.g., rudder speed) → either one shape per class or a SHACL-SPARQL rule
* **Group loads** with `PropellerLoadSet` + `hasMember` when a shape needs “all of {Fb, Ff, …} present”. (The property exists in context + graph.) 
* **Traceability**: always set `definedByRequirementSet` to `reg:TRAFICOM_2021`. 
* **Explainability**: add `message` and keep `rdfs:seeAlso` on shapes to point back to the intent.

---

## 8) Multi-agent mapping (how we’ll normalize corporate data later)

When a client drops a CSV/JSON with odd labels (e.g., *Powerrrr*), we’ll run a small pipeline:

1. **Resolver Agent (vocab mapping)**

   * Maps free-text keys to canon IRIs using `@context` terms, synonyms, and DNV/TEST.md hints.
   * Example: *Powerrrr* → `eng:mcrPower_kW` (or your chosen canonical for MCR power).

2. **Unit Agent (quantity normalization)**

   * Converts numbers to expected units (e.g., RPM → rev/s, kNm → N·m if needed; you already have units in `@context`).

3. **Shape Builder Agent**

   * Reads `ConstraintIntent` and emits/updates SHACL `PropertyShape`s with the right bounds and severity. 

4. **Evidence Agent**

   * Ensures each check carries `hasRegulationClause` with the correct § reference; can enrich `message` with human text from the clause.

5. **Validator Agent**

   * Runs SHACL, collects violations/warnings, and outputs a coverage report.

Because your ontology already encodes clauses and targets, this pipeline is straightforward; the heavy lifting is just the first mapping step.

---

## 9) Minimal workflow (day-to-day use)

1. **Ingest ship data** → map fields to canonical IRIs (step 8.1).
2. **Ensure prerequisites** per method (e.g., ducted prop: nozzle geometry; resonant: analysisMethod).
3. **Select requirement set** → `reg:TRAFICOM_2021`.
4. **Run SHACL** using your shapes (the two ready ones + any you add for §5 and §8).
5. **Read the report** → violations are your action items; warnings are advisories.
6. **Version & log** → update `meta:OntologyVersion*` info when you change rules/coverage. 

---

## 10) How to add a new rule (recipe)

* Create a `ConstraintIntent` with: `targetProperty`, bound (min/max/hasValue), `appliesWhen` (if conditional), `hasRegulationClause`, `definedByRequirementSet`, `severity`, `message`. 
* Create/extend a `shacl:PropertyShape`:

  * path = `targetProperty`
  * min/max/hasValue = from the intent
  * `rdfs:seeAlso` = the intent ID
* (Optional) For multi-thresholds (by class) either:

  * build one shape per class or
  * use SHACL-SPARQL to branch on `iceClass`.

---

## 11) Validation tips in a locked-down environment

* **Syntax only**: use a VS Code JSON validator extension (no admin rights needed).
* **Practical checks**: open `submitgpt.txt` and eyeball that `@context` and `@graph` close properly; you already have them correct.
* **Ground truth** for clauses: see TRAFICOM § indexes (Design Loads, Shaft line, Thrusters, Rudder, Materials) for exact wording you anchored.

---

## 12) Known limitations / next steps

* The `shape:rudderSpeedMinima` is a placeholder. Implement per-class shapes or SPARQL. 
* You may want shapes for: `torsionalVibrationMonitoring` (boolean, `appliesWhen iceClass ≥ IA`) and for **materials** thresholds by `materialKind`.
* If you decide to use QUDT `QuantityValue` everywhere, add those wrappers gradually (no need to refactor existing xsd numbers right now).

---

### One-screen mental model

* **Data** lives on components/systems (Propeller, Shafting, Thruster, Materials, Monitoring).
* **Rules** live as `ConstraintIntent` + SHACL shapes, with clear `hasRegulationClause`.
* **Normalization** maps client jargon → context IRIs.
* **Validation** = SHACL over your graph, with friendly messages and traceability back to §-anchors.

