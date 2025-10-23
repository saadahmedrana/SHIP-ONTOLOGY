import os, random, textwrap, json, csv
from datetime import datetime
from pathlib import Path

# Output folder (will create if missing)
OUT_DIR = Path("OEM_EXTRA")
OUT_DIR.mkdir(exist_ok=True)

PREFIXES = textwrap.dedent("""\
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix ssn:  <http://www.w3.org/ns/ssn/> .
@prefix fmu:  <http://example.com/fmu#> .
@prefix qudt: <http://qudt.org/2.1/schema/qudt#> .
@prefix unit: <http://qudt.org/2.1/vocab/unit#> .
""")

# canonical pool (shortened subset + new noise)
CANONICALS = [
    ("mcrPower_kW", "unit:KiloW", "eng:PrimeMover"),
    ("mcrRpm_revPerSec", "unit:REV-PER-SEC", "eng:PrimeMover"),
    ("qEmax_kNm", "unit:KiloN-M", "eng:PrimeMover"),
    ("seaChestVolume_m3", "unit:M3", "eng:CoolingWaterInletChest"),
    ("strainerOpenAreaRatio", None, "eng:CoolingWaterInletChest"),
    ("yieldStrength_MPa", "unit:MPa", "mat:MechanicalPropertySet"),
    ("D_m", "unit:M", "prop:Propeller"),
    ("P0_7_m", "unit:M", "prop:Propeller"),
    ("EAR", None, "prop:Propeller"),
    ("Qr_kNm", "unit:KiloN-M", "prop:ShaftingSystem"),
    ("Tr_kN", "unit:KiloN", "prop:ShaftingSystem"),
]

# typical messy OEM-style synonyms
NOISY_SYNONYMS = {
    "mcrPower_kW": ["Pwr_Out_kw", "MainPwr", "EngPowr", "PwrO", "OutKW_MCR", "kwPower"],
    "mcrRpm_revPerSec": ["nRPM_meas", "EngSpd_rps", "omega_eng", "RPMnom", "rpsVal"],
    "qEmax_kNm": ["TqMAX", "Qmax_tq", "MaxTQNm", "Tpeak", "TorqueMAX"],
    "seaChestVolume_m3": ["SeaChstVol", "Chst_Vol", "coolChestCap", "InletBoxVol"],
    "strainerOpenAreaRatio": ["strnOpnRat", "ScreenRatio", "areaOpenFact"],
    "yieldStrength_MPa": ["YldStrgth", "Y_S_MPa", "YieldMpa", "YStr"],
    "D_m": ["PropDia", "Dext", "PropDiam_m"],
    "P0_7_m": ["Pitch07", "Pitch0p7m", "P_07"],
    "EAR": ["EARval", "AEratio", "ExpAreaRat"],
    "Qr_kNm": ["RespTq", "QrNm", "ShTq", "ShaftQNm"],
    "Tr_kN": ["Thrst_kn", "ThrustDesign", "T_r_kN"],
}

# completely irrelevant / no-match variables
NO_MATCH = [
    ("PaintCoatingType", None, "hull:Coatings", "String indicating type of coating used."),
    ("SensorFaultFlag", None, "sys:Sensor", "Diagnostic flag for faulty sensor."),
    ("NoiseLevel_dB", "unit:DB", "env:Noise", "Noise level measurement in decibels."),
    ("AirTemp_degC", "unit:DEG_C", "env:Weather", "Ambient air temperature."),
    ("GPS_Latitude", None, "sys:Navigation", "Geographic latitude position."),
    ("HullVibration_mm_s", "unit:MM-PER-S", "hull:Structure", "Measured hull vibration velocity."),
]

def sample_value(unit):
    if not unit: return round(random.uniform(0.1, 10.0), 2)
    if "KiloW" in unit: return round(random.uniform(500, 10000), 1)
    if "REV-PER-SEC" in unit: return round(random.uniform(5, 25), 2)
    if "KiloN-M" in unit: return round(random.uniform(10, 900), 1)
    if "KiloN" in unit: return round(random.uniform(50, 2000), 1)
    if "M3" in unit: return round(random.uniform(1.0, 25.0), 2)
    if "MPa" in unit: return round(random.uniform(250, 800), 1)
    if "M" in unit: return round(random.uniform(0.3, 6.0), 3)
    return round(random.uniform(0.1, 5.0), 2)

def make_oem_file(oem_ns, brand):
    random.seed(hash(oem_ns))
    lines = [PREFIXES, f"@prefix {oem_ns}: <http://example.com/{oem_ns}#> .\n"]
    sys_iri = f"{oem_ns}:System001"
    lines.append(f"{sys_iri} a sosa:FeatureOfInterest, ssn:System ;\n")
    lines.append(f'  rdfs:label "{brand} Test System" .\n\n')

    mapping = []
    picks = random.sample(CANONICALS, k=random.randint(8, 10))

    for i, (canon, unit, dom) in enumerate(picks, 1):
        oem_name = random.choice(NOISY_SYNONYMS[canon])
        iri = f"{oem_ns}:Var{i:02d}"
        val = sample_value(unit)
        lines.append(f"{iri} a sosa:ObservableProperty ;\n")
        lines.append(f"  ssn:isPropertyOf {sys_iri} ;\n")
        lines.append(f'  fmu:hasFMUVariableName "{oem_name}" ;\n')
        if unit:
            lines.append(f"  qudt:unit {unit} ;\n")
        lines.append(f'  rdfs:comment "OEM variable from system datasheet ({brand})." .\n')
        lines.append(f"{iri}_Obs a sosa:Observation ;\n")
        lines.append(f"  sosa:observedProperty {iri} ;\n")
        lines.append(f'  sosa:hasSimpleResult "{val}"^^xsd:decimal .\n\n')
        mapping.append((oem_name, canon))

    # Add some random "no match" variables
    extras = random.sample(NO_MATCH, 3)
    for j, (nm, u, dom, desc) in enumerate(extras, 99):
        iri = f"{oem_ns}:Extra{j}"
        val = sample_value(u)
        lines.append(f"{iri} a sosa:ObservableProperty ;\n")
        lines.append(f"  ssn:isPropertyOf {sys_iri} ;\n")
        lines.append(f'  fmu:hasFMUVariableName "{nm}" ;\n')
        if u:
            lines.append(f"  qudt:unit {u} ;\n")
        lines.append(f'  rdfs:comment "{desc}" .\n')
        lines.append(f"{iri}_Obs a sosa:Observation ;\n")
        lines.append(f"  sosa:observedProperty {iri} ;\n")
        lines.append(f'  sosa:hasSimpleResult "{val}"^^xsd:decimal .\n\n')
        mapping.append((nm, None))  # None = no ontology match

    path = OUT_DIR / f"{oem_ns.upper()}_EXTRA.ttl"
    path.write_text("".join(lines), encoding="utf-8")
    return path, mapping

# Generate 3 OEMs with messy names
OEMS = [("oemx", "Poseidon Dynamics"), ("oemy", "Aurora Systems"), ("oemz", "OceanEdge Marine")]

rows = []
for ns, brand in OEMS:
    path, maplist = make_oem_file(ns, brand)
    for wrong, right in maplist:
        rows.append([path.name, ns, brand, wrong, right or "NO_MATCH"])

# Write reference mapping
csv_path = OUT_DIR / "extra_mapping.csv"
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["oem_file", "ns", "brand", "original_name", "canonical_id"])
    w.writerows(rows)

print(f"\n✅ Generated {len(OEMS)} extra OEM files with messy variable names.")
print(f"Files: {', '.join([p.name for p,_ in OEMS])}")
print(f"Mapping saved to {csv_path}")
