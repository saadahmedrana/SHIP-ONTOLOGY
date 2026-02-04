#!/usr/bin/env python3
import json
import sys
from copy import deepcopy

ID_MAP = {
    "PropulsionSystem": "prop:PropulsionSystem",
    "PrimeMover": "eng:PrimeMover",
    "ElectricMotor": "eng:ElectricMotor",
    "MotorOperatingLimits": "eng:MotorOperatingLimits",
    "MotorRatedPoint": "eng:MotorRatedPoint",
    "MotorEfficiencyPointSet": "eng:MotorEfficiencyPointSet",
    "MotorBearings": "eng:MotorBearings",
    "MotorFoundationInterface": "eng:MotorFoundationInterface",
    "MotorThermalProtection": "eng:MotorThermalProtection",
    "MotorSpaceHeater": "eng:MotorSpaceHeater",
    "MotorVFDConstraints": "eng:MotorVFDConstraints",
    "MotorEquivalentCircuit": "eng:MotorEquivalentCircuit",

    "TransmissionSystem": "prop:TransmissionSystem",
    "ShaftingSystem": "prop:ShaftingSystem",

    "Gearbox": "comp:Gearbox",
    "Coupling": "comp:Coupling",
    "PropulsorSystem": "prop:PropulsorSystem",

    "Propeller": "comp:Propeller",
    "Nozzle": "comp:Nozzle",
    "HubAndCPMechanism": "comp:HubAndCPMechanism",

    "ThrusterSystem": "prop:ThrusterSystem",
    "Sensor": "prop:Sensor",
    "MonitoringEvent": "prop:MonitoringEvent",

    "MaterialsRequirements": "mat:MaterialsRequirements",
    "MaterialSample": "mat:MaterialSample",
    "MechanicalPropertySet": "mat:MechanicalPropertySet",
}

KEY_MAP = {
    "prop:hasMember": "hasMember",
}

def transform(obj):
    if isinstance(obj, dict):
        newd = {}
        for k, v in obj.items():
            k2 = KEY_MAP.get(k, k)

            if k2 == "@id" and isinstance(v, str) and v in ID_MAP:
                v2 = ID_MAP[v]
            elif k2 == "@type" and isinstance(v, str) and v in ID_MAP:
                v2 = ID_MAP[v]
            else:
                v2 = transform(v)

            newd[k2] = v2
        return newd

    if isinstance(obj, list):
        return [transform(x) for x in obj]

    # Optional: also map *string values* in graph that exactly match the bad IDs.
    if isinstance(obj, str) and obj in ID_MAP:
        return ID_MAP[obj]

    return obj

def main():
    if len(sys.argv) != 3:
        print("Usage: python fix_jsonld_ids.py input.jsonld output.jsonld")
        sys.exit(1)

    inp, outp = sys.argv[1], sys.argv[2]
    with open(inp, "r", encoding="utf-8") as f:
        data = json.load(f)

    fixed = deepcopy(data)

    # ✅ Do NOT touch @context
    if "@graph" in fixed:
        fixed["@graph"] = transform(fixed["@graph"])
    else:
        # fallback: if graph is absent, do nothing instead of risking context edits
        print("⚠️ No @graph found; not modifying anything.")
        sys.exit(2)

    with open(outp, "w", encoding="utf-8") as f:
        json.dump(fixed, f, ensure_ascii=False, indent=2)

    print(f"✅ Wrote fixed JSON-LD to: {outp}")

if __name__ == "__main__":
    main()
