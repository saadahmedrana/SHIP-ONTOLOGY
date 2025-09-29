# Ship Ontology — Propulsion & Powertrain (Working Outline v0.1)
**Scope:** Propulsion & powertrain, with the necessary hull/structural context to support SHACL constraints from the Finnish Ice Class Regulations (2021).  
**Style:** PascalCase for Classes; lowerCamelCase for properties.  
**Property types:** *Object properties* (→ link two resources) and *Data properties* (→ scalar values; always include units).  
**Status:** Draft/TBD — stable enough to iterate on; placeholders marked `TBD`.

---

## 0. Conventions & Enums

### 0.1 Enums (controlled vocabularies)
- **IceClass**: `IASuper`, `IA`, `IB`, `IC`, `II`, `III`  
- **HullRegion**: `Bow`, `Midbody`, `Stern`  
- **SpecialStrengthZones**: `UpperBowIceBeltRegion`, `ForefootRegion`  
- **Orientation**: `longitudinal`, `transverse`  
- **SupportType**: `deck`, `stringer`, `bulkhead`, `tankTop`, `webFrame`

### 0.2 Units (recommend QUDT later)
Keep `{value, unit}` for each numeric data property, e.g. `{"value": 22, "unit": "mm"}`. (TBD: adopt QUDT vocabulary.)

---

## 090 General
### 090.1 RegulatoryRegion
Instances (as *HullRegion* or *SpecialStrengthZones*):
- `Bow`  
- `Midbody`  
- `Stern`  
- `UpperBowIceBeltRegion`  
- `ForefootRegion`

### 090.2 IceClass
Instances: `IASuper`, `IA`, `IB`, `IC`, `II`, `III`

---

## 100 MainStructure

### 101 StructuralMaterials
- **Steel**
  - `NormalStrengthSteel235` (σ_y ≈ 235 MPa)
  - `HighStrengthSteel315` (σ_y ≥ 315 MPa)
- **Other Materials**: `Aluminium`, `Composite`, `Concrete`, `Wood`, `Bronze`, `NodularCastIron`, `AusteniticSteel`  
- **MaterialRequirements (sea-water exposed propulsion parts)**  
  - `elongation ≥ 15 %` (test specimen GL=5·D)  
  - `CharpyV at −10 °C`: 20 J (not required for `Bronze` and `AusteniticSteel`); for `NodularCastIron`: 10 J at −10 °C.  
  - (Attach to relevant components via `hasMaterial`.)

### 102 CorrosionPreventionSystems
- `Coating`, `SacrificialAnode`, `ImpressedCurrentSystem`, `CathodicProtectionMonitoring`

### 103 StructuralFabricationSystem
- `Welded` (TBD: extend to `Riveted`, `Bolted` if ever needed)

### 104 Voids
- `VoidSpace` (TBD details)

### 105 Tonnage
- `GrossTonnage`, `NetTonnage` (TBD detail)

### 106 MarkingsOnStructure
- `VesselIdentificationMarks`, `DraughtMarks`, `LoadLineMarks`, `TonnageMarks`, `BottomSurveyMarks`, `BulkCarrierDeltaMarks`  
- `IceClassDraughtMark` (warning triangle + “ICE” mark; see regulatory anchors)
  - Data props: `triangleHeight`, `triangleSideLength`, `offsetAbaftLoadLine`

---

## 110 ShipStructure

### 111 ShipHullStructure (Assembly)
**RegulatoryVariables** (Data properties, attach to `Ship` or `ShipHullStructure` as appropriate):
- `L` (m), `LBOW` (m), `LPAR` (m), `B` (m)
- `T` (m) actual ice-class draughts (`UIWL` and `LIWL`-specific)
- `Awf` (m²) — bow waterline area
- `alpha` (deg) — waterline angle at B/4
- `phi1` (deg) — stem rake at centerline
- `phi2` (deg) — bow rake at B/4
- `psi` (deg) — flare angle (derived; keep if needed)
- `DP` (m) — propeller diameter
- `HM` (m), `HF` (m) — brash ice thicknesses
- `delta` (t) — ship displacement at ice-class draught
- `UIWL` (m), `LIWL` (m) — upper/lower ice waterlines

#### 111.1 Deck
- **Object props:** `isAttachedTo: Frame` (where relevant)
- **Data props:** `deckThickness`, `deckMaterial` (via `hasMaterial`), `locatedInHullRegion`

#### 111.2 Bulkhead (Transverse)  
#### 111.3 Bulkhead (Longitudinal)
- **Object props:** `isAttachedTo: Frame`
- **Data props:** `spacing`, `thickness`, `locatedInHullRegion`

#### 111.4 Sides
- **111.41 SidePlate**
  - **Object props:** `locatedInHullRegion`, `hasMaterial`
  - **Data props:** `thickness`, `iceBeltVerticalExtentTop`, `iceBeltVerticalExtentBottom`
- **111.42 SideStiffening**
  - **Frame**
    - **Object props:** `isAttachedTo: Deck`, `locatedInHullRegion`, `hasSupportType`, `hasOrientation`
    - **Data props:** `span`, `spacing`, `sectionModulusZ`, `shearAreaA`
  - **WebFrame**
    - **Data props:** `span`, `sectionModulusZ`, `shearAreaA`
  - **Stringer / IceStringer**
    - **Data props:** `span`, `sectionModulusZ`, `shearAreaA`

#### 111.5 Bow
- **Data props:** `LBOW`, `Awf`, `alpha`
- **111.51 Stem & Bow Geometry**
  - `phi1` (stem rake), `phi2` (bow rake), `psi` (flare; derived), `stemConstructionType` (rolled/cast/forged/shaped plate)
- **111.52 BulbousBow**
  - `hasBulbousBow` (boolean)

#### 111.6 Stern
- **SternFrame** (TBD: attributes)
- **Object props:** link to `PropulsionSystem` (`isAttachedTo`, `clearances`)  

---

# 120 Propulsion System Module — Draft v0.3 (Ice-Class Focus)

**Scope:** Comprehensive propulsion-side ontology needed to constrain design per the Finnish Ice Class Regulations (2021), aligned with DNV GMOD naming where sensible. Engine-focused requirements are in section *130 Engine Module*; this file covers the rest of propulsion: propellers, nozzles, hubs/CP mechanisms, shaft line, bearings/seals, couplings/gearbox, and azimuthing thrusters.  
**Style:** PascalCase for classes; lowerCamelCase for properties; data properties always carry units.  
**Audience:** For SHACL later; not JSON-LD yet. Use this as a working catalogue of classes, properties, and rule stubs.

---

## 120.0 Conventions & Enums

### 120.0.1 Controlled Vocabularies
- **PropellerType:** `open`, `ducted`  
- **PitchType:** `FP` (fixed pitch), `CP` (controllable pitch)  
- **PropulsorArrangement:** `singleScrew`, `twinScrew`, `tripleScrew`  
- **ThrusterType:** `azimuthingZDrive`, `azimuthingLDrive`, `podded`, `rimDriven` (TBD scope)  
- **ThrusterMode:** `pushing`, `pulling`  
- **BearingType:** `thrust`, `sternTubeAft`, `sternTubeFwd`, `lineBearing`  
- **SealType:** `simpleLip`, `doubleLip`, `faceSeal` (TBD)  
- **CouplingType:** `rigid`, `flexible`, `clutch`  
- **MaterialKind:** `bronze`, `austeniticSteel`, `nodularCastIron`, `steel`, `aluminium`, `composite`

### 120.0.2 Units
Keep each scalar as `{value, unit}`; examples: length `m`, area `m²`, force `kN`, torque `kNm`, speed `rpm` (or `rev/s` consistently), thickness `mm`, angle `deg`.

---

## 120.1 Classes & Subassemblies

### 120.1.1 PropulsionSystem (Assembly)
- **Object props:**  
  - `hasPropulsor: Propeller | AzimuthingThruster` (1..*)  
  - `hasShaftLine: ShaftLine` (1..*)  
  - `hasGearbox: Gearbox` (0..1)  
  - `hasCoupling: Coupling` (1..*)  
  - `hasControlAndMonitoring: ControlAndMonitoring` (0..1)
- **Data props:**  
  - `propulsorArrangement: PropulsorArrangement`  
  - `iceClass: IceClass` (mirror from ship for local SHACL checks)

### 120.1.2 Propeller (Open or Ducted)
- **Object props:**  
  - `propellerType: PropellerType`  
  - `pitchType: PitchType`  
  - `hasNozzle: Nozzle` (only if `propellerType=ducted`)  
  - `hasHubAndPitchMechanism: HubAndCPMechanism` (if `pitchType=CP`)  
  - `material: MaterialKind`
- **Geometry data props:**  
  - `D` (m) — diameter  
  - `Z` (–) — blades  
  - `P0_7` (m) — pitch at 0.7R  
  - `c0_7` (m) — chord at 0.7R  
  - `EAR` (–) — expanded area ratio  
  - `hubDiameter_d` (m)  
  - `skewAt0_7R` (deg), `rakeAt0_7R` (deg) (TBD if needed)
- **Operational data props:**  
  - `nn` (rpm) — nominal speed at MCR in open water  
  - `n_bollard` (rpm) — MCR in bollard condition (rule defaults exist if unknown)  
  - `serviceSpeed` (kn)  
- **Load variables (see §120.2):** `Fb`, `Ff`, `Qsmax`, `Tb`, `Tf`, `Qmax`

### 120.1.3 Nozzle (for ducted props)
- **Data props:** `lipThickness` (mm), `inletRadius` (mm), `throatDiameter` (m), `length` (m), `nozzleType` (e.g., 19A/37; enum TBD)  
- **Object props:** `material`, `stiffeningToHull` (Frames/Stringers link), `isAttachedTo: SternStructure`

### 120.1.4 HubAndCPMechanism (for CP propellers)
- **Data props:** `maxBladeAngle` (deg), `minBladeAngle` (deg), `actuationPressure` (bar), `boltDesignForFex` (boolean)  
- **Note:** Dimension against **blade failure load Fex** so blade loss doesn’t damage bossing/shaft/bearings.

### 120.1.5 ShaftLine
- **Components:** `IntermediateShaft`(s), `SternTubeAssembly`, `ShaftSeals`, `Bearings` (thrust/stern tube/line), `Couplings`  
- **Data props:**  
  - `Qr` (kNm) — design response torque along shaft line  
  - `Tr` (kN) — design response thrust along shaft line  
  - `resonanceWithin20pctOfMaxSpeed` (boolean)  
  - `safetyFactorExtremeYield` (–), `safetyFactorFatigue` (–), `safetyFactorBladeFailureYield` (–)
- **Object props:** `hasBearing`, `hasSeal`, `hasSternTube`

### 120.1.6 Bearings
- **Data props (per bearing):** `bearingType`, `ratedLoad` (kN), `allowableContactPressure` (MPa), `lubricationType` (TBD), `cooling` (TBD)

### 120.1.7 ShaftSeals
- **Data props:** `sealType`, `designPressure` (bar), `redundancy` (boolean)

### 120.1.8 Coupling
- **Data props:** `couplingType`, `ratedTorque` (kNm), `maxMisalignment` (mrad)

### 120.1.9 Gearbox
- **Data props:** `gearRatio` (–), `ratedTorque` (kNm), `torsionalStiffness` (kNm/rad), `efficiency` (–)

### 120.1.10 AzimuthingThruster
- **Object props:** `thrusterType`, `thrusterMode`, `propeller: Propeller` (reuses `propellerType`/`pitchType`), `hasNozzle` (optional)  
- **Geometry data:** `projectedAreaAt` (m²), `stemToHullClearance` (m)  
- **Design variables:** `Fti` (kN), `Ftr` (kN), `globalVibrationCheck` (boolean)  
- **Placement/immersion:** `Hiced` (m), `hi` (m); `locationFactor_k1` (–)

### 120.1.11 ControlAndMonitoring
- **Data props:** `torsionalVibrationMonitoring` (boolean), `bladeLoadMonitoring` (boolean), `alarmSetpoints` (list; TBD)

---

## 120.2 Load Variables & Definitions (bind in SHACL)

### 120.2.1 Blade Loads (TRAFICOM §6.5.1)
- `Fb` (kN) — maximum backward blade force  
- `Ff` (kN) — maximum forward blade force  
- `Qsmax` (kNm) — maximum blade spindle torque  
- `loadedArea` (m²) — rule-defined area (open/ducted variants)  
- `loadDistribution` (–) — distribution pattern reference  
- `Nice` (–) — lifetime ice load count (multiply by `Z` if all blades are involved)

### 120.2.2 Axial Loads (TRAFICOM §6.5.2)
- `Tb` (kN), `Tf` (kN) — backward/forward maximum ice thrust on propeller (all blades)  
- `Tr` (kN) — design response thrust along the shaft line

### 120.2.3 Torsional Loads (TRAFICOM §6.5.3)
- `Qmax` (kNm) — propeller ice torque (blade-level; open vs ducted formulas differ; `n_limit` switch)  
- `Qr` (kNm) — design response torque along shaft line  
- `Qemax` (kNm) — prime mover max torque (defaults exist when unknown)  
- `n_limit` (rpm) — break-point speed for formula selection  
- Flags: `isResonantCase` (boolean), `analysisMethod` (`timeDomain`/`frequencyDomain`)

### 120.2.4 Blade Failure Load (TRAFICOM §6.5.4)
- `Fex` (kN) — ultimate bending force at 0.8R; blade loss criterion  
- `Qsex` (kNm) — ultimate spindle torque (if applicable)

### 120.2.5 Ice & Operation Parameters (TRAFICOM §6.3)
- `Hice` (m) — design block thickness by class  
- `Hiced` (m) — 2/3·Hice (thruster cases)  
- `Nclass` (–) — class-based impacts-in-life  
- `k1` (–) — propeller location factor (centre/wing/pulling)  
- `k2` (–) — submersion factor from immersion function `f`  
- `k3` (–) — machinery type factor (`1` fixed, `1.2` azimuthing)  
- `fImmersion` (–) — immersion function needing `h0`, `Cice`, `D`

---

## 120.3 Design Principles & Acceptance (Propeller & Bossing)

### 120.3.1 Propeller Blade Stress / Acceptance
Compute blade stresses under `Fb`/`Ff`/`Qsmax` using rule load distributions/areas. Acceptability requires meeting stress limits; fatigue uses S–N curves (two-slope or constant-slope), equivalent stress at 10^8 cycles. For two-slope materials, an exemption inequality with `B1,B2,B3` may apply.

### 120.3.2 Fatigue Design (S–N Parameters)
Define: `sigma_fat` (MPa), `rho` factor, slope `m`, reductions `gamma_eps1`, `gamma_eps2`, `gamma_n`, `gamma_m`. Keep table-driven `C1..C4` (ρ) and `B1..B3` (exemption) ready.

### 120.3.3 CP Mechanism & Bossing
Dimension for `Fex` so blade failure does not damage bossing, shaft, bearings, or thrust bearing.

---

## 120.4 Shaft Line Design

### 120.4.1 Strength & Fatigue Factors
Withstand §120.2 loads with **minimum safety factors**: `extremeYield ≥ 1.3`, `fatigue ≥ 1.5`, `bladeFailureYield ≥ 1.0`.

### 120.4.2 Torsional Response
- **Non-resonant:** prescriptive design torque method (depends on engine/propeller).  
- **Resonant:** **dynamic** torsional analysis (time/frequency domain); cover MCR, MCR bollard, and resonant speeds; include phase variation between ice excitation and prime mover excitation.

### 120.4.3 Bearings & Seals
Dimension bearings for `Tr` and combined loads; seals for pressure/abrasion (TBD details).

---

## 120.5 Azimuthing Main Propulsors

### 120.5.1 Design Principle
In addition to propeller blade rules, design **thruster body** and **slewing/steering** systems for extreme loads and global vibration.

### 120.5.2 Extreme Loads (thruster body / hub / ridge)
- **Ice impact on body or hub:** `Fti` (kN) once-in-lifetime extreme.  
- **Ridge penetration loads:** `Ftr` (kN), with load cases T4/T5 (symmetric/asymmetric, longitudinal/lateral).  
- **Global vibration:** Check natural frequencies (longitudinal/transverse) incl. added mass & damping; include ship attachment stiffness.

### 120.5.3 Parameters by Class for Ridge Loads
Provide per-class `Hr` (m), consolidated layer thickness, and initial penetration speeds; bind to load cases (aft vs thruster-first modes).

### 120.5.4 Acceptance & Detailing
Steering mechanism, unit fitting, and body to withstand **plastic bending of a blade** without damage; check “top-down” blade orientation as worst case.

---

## 120.6 SHACL Rule Stubs (Natural Language)

> *Constraint intents* you’ll later implement in SHACL. Each rule references symbols above and uses `iceClass`.

### A. Propeller Ice Torque — Open vs Ducted
- If `propellerType=open`: compute `Qmax` with open-prop formula using `D`, `d`, `P0_7/D`, `c0_7`, `n_bollard`, `Hice` (switch at `n_limit`). If `n_bollard` unknown, apply rule defaults.  
- If `propellerType=ducted`: compute `Qmax` with ducted-prop formula (piecewise in `n ≤/> n_limit`).

### B. Axial Design Loads
Compute `Tb` and `Tf`; derive `Tr` for shaft sizing.

### C. Blade Loads & Counts
Compute `Fb`, `Ff`, `Qsmax`; set `Nice = k1*k2*k3*Nclass`; if component sees **all blades**, multiply by `Z`.

### D. Shaft Line Design Factors
Enforce: `extremeYield ≥ 1.3`, `fatigue ≥ 1.5`, `bladeFailureYield ≥ 1.0`.  
If `resonanceWithin20pctOfMaxSpeed = true` ⇒ `analysisMethod ∈ {timeDomain, frequencyDomain}` and results for `Qr` across **MCR**, **MCR bollard**, **resonant**.

### E. CP/Bossing Blade-Failure Integrity
If `pitchType=CP` ⇒ `boltDesignForFex = true` and check hub/bossing/shaft don’t yield under `Fex`/`Qsex`.

### F. Thruster Extreme Loads & Vibration
For any `AzimuthingThruster`: compute `Fti` and `Ftr` for T4a/T4b/T5a/T5b; limit vertical contact area by `Hr`. Ensure `globalVibrationCheck=true` and modal analysis includes added mass/damping + attachment stiffness.

### G. Propeller Immersion & Location Factors
Compute `k2` from immersion function (`h0`, `Cice`, `D`); apply `k1` by propeller location and `k3` by machinery type. If propeller immersion is less than class `hi`, flag stricter requirement/warning.

### H. Stern-Hull Clearance
Enforce minimum clearance `≥ h0` to avoid excessive blade tip loads (applies to stern geometry).

---

## 120.7 Minimal Property Sets (by Component)

### 120.7.1 Propeller
`propellerType`, `pitchType`, `D`, `Z`, `P0_7`, `c0_7`, `EAR`, `hubDiameter_d`, `nn`, `n_bollard`, `material`, `serviceSpeed`; computed: `Fb`, `Ff`, `Qsmax`, `Tb`, `Tf`, `Qmax`.

### 120.7.2 ShaftLine
`Qr`, `Tr`, `resonanceWithin20pctOfMaxSpeed`, `analysisMethod`, safety factors; per bearing: `bearingType`, `ratedLoad`.

### 120.7.3 Nozzle
`lipThickness`, `inletRadius`, `throatDiameter`, `length`, `nozzleType`, `material`.

### 120.7.4 HubAndCPMechanism
`maxBladeAngle`, `minBladeAngle`, `actuationPressure`, `boltDesignForFex`.

### 120.7.5 AzimuthingThruster
`thrusterType`, `thrusterMode`, `projectedAreaAt`, `Hiced`, `hi`, `locationFactor_k1`; computed: `Fti`, `Ftr`, `globalVibrationCheck`.

---

## 120.8 Notes / Open TODOs
- Add formula parameters & constants inline (from regulation tables) when converting to SHACL/JSON-LD; keep symbol names now to avoid copy errors.  
- Consider `NozzleType` enum (19A/37/etc.).  
- Add stern-frame clearances & hull reinforcement notes for multi-screw arrangements.  
- Add a `MonitoringEvent` node to capture measured `Qr/Tr` exceedances during operation.
## Relationships (Object Properties)
- `hasIceClass` (Ship → IceClass)
- `locatedInHullRegion` (StructuralElement → HullRegion)
- `hasComponent` (Assembly → Component)  — multi-valued
- `hasRegulatoryVariable` (Ship/Hull/Propulsion → RegulatoryVariable) — or attach data props directly
- `isAttachedTo` (StructuralElement → SupportingElement)
- `hasMaterial` (Component → Material)
- `hasOrientation` (StructuralElement → Orientation)
- `hasSupportType` (StructuralElement → SupportType)

## Scalar (Data) Properties (selection)
- Geometry: `thickness`, `span`, `spacing`, `sectionModulusZ`, `shearAreaA`, `rakeAngle`, `flareAngle`
- Bow: `LBOW`, `Awf`, `alpha`, `phi1`, `phi2`, `psi`, `hasBulbousBow`
- Draught/Lines: `UIWL`, `LIWL`, `T`
- Propulsion: `D`, `P0_7`, `n`, `nn`, `EAR`, `serviceSpeed`
- Materials: `yieldStrength`, `charpyV`, `elongation`
- Loads: `Fb`, `Ff`, `Qsmax`, `Tb`, `Tf`, `Qmax`, `Qr`, `Tr`, `Fti`, `Ftr`, `Hice`, `hi`

---

## Example “RegulatoryVariables” Catalogue (for reuse in SHACL)
- `LengthBetweenPerpendiculars` (`L`, m)
- `LengthBow` (`LBOW`, m)
- `LengthParallelMidbody` (`LPAR`, m)
- `Breadth` (`B`, m)
- `IceClassDraught` (`T`, m; contextualized at `UIWL` and `LIWL`)
- `BowWaterlineArea` (`Awf`, m²)
- `WaterlineAngleAtBQuarter` (`alpha`, deg)
- `StemRake` (`phi1`, deg)
- `BowRakeAtBQuarter` (`phi2`, deg)
- `PropellerDiameter` (`DP`, m)
- `BrashIceThicknessMidChannel` (`HM`, m)
- `BrashIceThicknessDisplacedByBow` (`HF`, m)
- `DisplacementAtIceClassDraught` (`delta`, t)

---

## Natural-Language Rule Stubs (for SHACL later)

- **Upper Bow Ice Belt requirement**  
  If `hasIceClass ∈ {IASuper, IA}` **and** `serviceSpeed ≥ 18 kn` ⇒ require `UpperBowIceBeltRegion` strengthening with midbody-region scantling rules. (Attach to `SidePlate` in bow.)

- **Forefoot strengthening (IASuper)**  
  If `hasIceClass = IASuper` ⇒ require `ForefootRegion` strengthening below the ice belt from stem to ≥ five main frame spacings abaft the point where the bow profile departs from the keel line.

- **Propeller immersion check**  
  If highest point of propeller depth `< hi` below water surface in ballast **and** `hasIceClass ∈ {IB, IC}` ⇒ design propulsion system per `IA` requirements.

- **Rudder design speed minimums**  
  Min service speed for rudder design by class: IASuper: 20 kn; IA: 18 kn; IB: 16 kn; IC: 14 kn. Use actual service speed if higher.

(Exact equations and constants live in the regulation; we’ll bind SHACL constraints to these variables.)

---




130.0 Conventions

Units: All numerics carry {value, unit} (e.g., {750, "kW"}); angles “deg”, torque “kNm”, speed “rev/s” or “rpm”, time “h”, volume “m³”.

Enums (controlled vocab):

PrimeMoverType: twoStrokeDiesel, fourStrokeDiesel, dualFuelEngine, gasEngine, gasTurbine, steamTurbine, electricMotor (for hybrids).

StartingMethod: airStart, electricStart, hydraulicStart.

FuelKind: HFO, MDO, MGO, LNG, methanol, other (TBD list).

CouplingType: rigid, flexible, clutch.

CoolingCircuit: seaWaterOpenLoop, freshWaterClosedLoop.

130.1 Classes (Engine & Subsystems)
130.1.1 PrimeMover (Engine)

Key data props

primeMoverType: PrimeMoverType

mcrPower (kW) — maximum continuous rating

mcrSpeed (rev/s) or mcrRpm (rpm)

reversible (boolean) — needs reversing for astern

qEmax (kNm) — maximum engine torque (per rules/defaults; see anchors)

requiresBladeOrderResonanceAssessment (boolean) — torsional resonance check per TRAFICOM §6.5.3.4.

Object props

isConnectedTo: ShaftLine

hasFuelSystem: FuelSystem

hasStartingSystem: StartingAirSystem | ElectricStartSystem

hasCoolingSystem: CoolingWaterSystem

hasLubricatingOilSystem: LubricatingOilSystem

hasGovernor: Governor (TBD)

hasTurbocharger: Turbocharger (TBD)

130.1.2 ShaftLine (interface node for engine-side constraints)

Key data props:

designResponseTorqueQr (kNm), designResponseThrustTr (kN) — used for shaft components; include dynamic magnification when applicable.

hasFirstBladeOrderResonance (boolean)

Notes: If resonance present in ±20% of max operating speed, dynamic analysis is required (time or frequency domain).

130.1.3 FuelSystem (engine supply side)

Subcomponents: StorageTanks, DayTank/ServiceTank, TransferPumps, CentrifugalSeparators, BoosterSystem, FuelHeaters, ViscosityController, Filters, FuelMeters.

Design targets: Deliver fuel with correct viscosity & pressure across engine power range; redundancy in heaters; representative sampling; two bunker batches handled without mixing. 
Squarespace

Key data props:

deliveredViscosity (cSt @ temp)

heaterSurfaceTempLimit (°C) — typically ≤170 °C (steam) / 200 °C (thermal oil). 
Squarespace

boosterFlowCapacityAt120pct (kg/h) — heaters sized for 120% of max fuel consumption. 
Squarespace

samplingPointsProvided (boolean) — before/after separator. 
Squarespace

Object props: hasBoosterSystem, hasSeparator, hasHeater, hasViscosityController

130.1.4 StartingAirSystem (when StartingMethod = airStart)

Key data props (TRAFICOM §7.1):

airReceiverCapacity (Nm³ @ pressure) — sufficient for ≥12 consecutive starts if engine must be reversed to go astern; ≥6 if not reversible.

compressorChargeTime (h) — receivers charged from atmospheric to full pressure in ≤1 h; for IA Super & reversible, ≤0.5 h.

Object props: hasAirReceivers, hasCompressors, servesEngine: PrimeMover

130.1.5 CoolingWaterSystem (sea inlet / chest focus)

Key data props (TRAFICOM §7.2):

seaChestVolume (m³) — guidance ≈ 1 m³ per 750 kW total engine output (incl. essential auxiliaries).

strainerOpenAreaRatio (–) — ≥4× inlet pipe sectional area.

dischargeRecirculationProvided (boolean) — full-capacity discharge line back to chest.

locationNearCenterlineAft (boolean), iceAccumulationHeadroom (boolean).

Object props: hasSeaChest, hasStrainers, servesEngine: PrimeMover

130.1.6 LubricatingOilSystem

Key data props: pumpRedundancy (boolean), oilTemperatureRange (°C) (TBD per maker/Rules)

Object props: hasLOPump, hasCooler, servesEngine: PrimeMover

130.1.7 Coupling/Gear Interface (between engine ↔ shaft/propulsor)

Key data props: couplingType, ratedTorque (kNm), allowableMisalignment (mrad)

Notes: When calculating design torque without resonance, use combined engine & propeller contributions with inertia ratio Ie/It (per TRAFICOM §6.5.3.3).

130.2 Regulatory Variables (Engine-side) for SHACL

Ke (kW) — required engine output (attach to ship/engine context; from TRAFICOM §3). Use C-coefficients & constraints defined in §3 tables.

Qemax (kNm) — maximum engine torque; defaults per propulsor type when unknown (Table 6-10).

Qmax (kNm) — propeller ice torque; feed into shaft line response rules.

Qr, Tr — design response torque/thrust along shaft line, including dynamic magnification factors where prescribed.

Nclass, Nice — impacts count for fatigue design by ice class.

130.3 Engine-Focused SHACL Rule Stubs (natural-language; to implement later)

Starting air capacity (ice-class dependent)
If hasIceClass ∈ {IASuper, IA, IB, IC} and engine.startingMethod = airStart:

Require airReceiverCapacity to support ≥12 consecutive starts for reversible engines, or ≥6 if not reversible;

Require compressorChargeTime ≤ 0.5 h for IASuper & reversible, else ≤ 1 h.

Cooling sea chest sizing for ice
If navigating in ice (any class in scope):

Provide seaChestVolume ≈ 1 m³ per 750 kW total engine power (incl. necessary auxiliaries);

Provide strainerOpenAreaRatio ≥ 4.

Provide dischargeRecirculationProvided = true, locationNearCenterlineAft = true, iceAccumulationHeadroom = true.

Design torque / resonance method selection
If hasFirstBladeOrderResonance = true within ±20% of max operating speed:

Compute Qpeak via dynamic torsional analysis (time- or frequency-domain per §6.5.3.4).
Else (no relevant resonance):

Compute design torque using non-resonant formulas with Ie/It contribution (TRAFICOM §6.5.3.3).

Default Qemax when unknown
If prime mover type known but Qemax unknown, set per Table 6-10 defaults (e.g., FP diesel = 0.75·Qn; CP electric = Qmotor).

Fuel treatment performance
Fuel system shall: (a) reduce impurities to safe level for diesel engine use, (b) deliver correct viscosity/pressure across power range, (c) include redundant heaters sized for 120% flow, and (d) provide sampling before/after separators and viscosity control with PI action. (Map to FuelSystem & subcomponents.) 
Squarespace

130.4 TRAFICOM Anchor Map (engine-relevant only)

§3 ENGINE OUTPUT — definitions, coefficients, class-wise powering requirement Ke; attach to ship/engine.

§6 PROPULSION MACHINERY — scope & definitions (Fb, Ff, Qmax, Qr, Tr, Nclass, etc.); axial/thrust/torque design loads; fatigue cycles; azimuthing cases.

§6.5.3.3 / §6.5.3.4 — design torque rules (non-resonant vs resonant dynamic analysis; time/frequency domain).

§7.1 STARTING ARRANGEMENTS — number of consecutive starts; compressor charging times.

§7.2 SEA INLET & COOLING — sea chest volume guidance; strainer area; location & piping.

130.5 DNV Alignment Notes (for model hygiene)

Fuel treatment/conditioning (residuals): Use DNV structure & doc verbs for FuelSystem: booster system, centrifugal separators, heaters with redundancy, PI viscosity controller, sampling points, minimum heater performance (120% flow), surface temperature limits. Bind your data properties to these. 
Squarespace

Gas-fuelled installations (if applicable later): Keep a placeholder GasFuelSupplySystem and reference DNV Pt.6 Ch.2 “Gas fuelled ship installations” for documentation and certification hooks. (You can expand once propulsion fuel scope requires it.) 
Squarespace

130.6 Minimal Property Set (engine instances)

For every PrimeMover instance you should be able to fill:

Identity: primeMoverType, reversible, couplingType

Ratings: mcrPower {kW}, mcrSpeed {rev/s|rpm}, qEmax {kNm}

Starting (if airStart): airReceiverCapacity, compressorChargeTime

Cooling: seaChestVolume, strainerOpenAreaRatio, dischargeRecirculationProvided, locationNearCenterlineAft, iceAccumulationHeadroom

Shaftline interface: hasFirstBladeOrderResonance, designResponseTorqueQr, designResponseThrustTr

Fuel system: deliveredViscosity, boosterFlowCapacityAt120pct, heaterSurfaceTempLimit, samplingPointsProvided

130.7 Open TODOs (engine module)

Add maker-specific governor/turbocharger parameters (rpm limits, transient torque multipliers).

Add explicit Ke calculation artifacts (C₁…C₅, f₁…f₄, g₁…g₃) as reusable variables to back SHACL checks for powering (§3) — keep as references to the regulation tables to avoid copy errors.

If azimuthing main propulsors are present, mirror TRAFICOM §6.6.5 load scenarios into a ThrusterIntegration node (impact & ridge penetration loads; global vibration acceptance




## Notes / Open TODOs
- Attach `iceBeltVerticalExtentTop/Bottom` from table values per `HullRegion` & `IceClass`.  
- Add formulas for `Frame` Z and A (section modulus and shear area) as computed attributes or as constraints (TBD).  
- Add `CoolingWaterSystem` & `SeaChest` constraints (ice operations).  
- Reconcile `MarkingsOnStructure` with actual layout details on hull (UIWL/LIWL).  
- Consider aligning to DNV GMOD identifiers in `@id` patterns later for JSON-LD mapping.
