import pandas as pd

# new OEM rows
new_rows = [
    # --- OEMM ---
    ["OEMM_OEM.ttl", "oemm", "Maritech Systems", "oemm:Var01", "PwEng_MCR", "unit:KiloW", "mcrPower_kW", "eng:PrimeMover"],
    ["OEMM_OEM.ttl", "oemm", "Maritech Systems", "oemm:Var02", "QdrvMx", "unit:KiloN-M", "qEmax_kNm", "eng:PrimeMover"],
    ["OEMM_OEM.ttl", "oemm", "Maritech Systems", "oemm:Var03", "SeaChtVlm", "unit:M3", "seaChestVolume_m3", "eng:CoolingWaterInletChest"],
    ["OEMM_OEM.ttl", "oemm", "Maritech Systems", "oemm:Var04", "AirCap_nm3", "unit:M3", "airReceiverCapacity_Nm3", "eng:StartingSystem"],
    ["OEMM_OEM.ttl", "oemm", "Maritech Systems", "oemm:Var05", "PaintThickness_um", "unit:MM", "", ""],

    # --- OEMN ---
    ["OEMN_OEM.ttl", "oemn", "PolarMarine Ltd", "oemn:Var01", "Nnom_rpm", "unit:REV-PER-MIN", "nn_rpm", "prop:Propeller"],
    ["OEMN_OEM.ttl", "oemn", "PolarMarine Ltd", "oemn:Var02", "Dprop_m", "unit:M", "D_m", "prop:Propeller"],
    ["OEMN_OEM.ttl", "oemn", "PolarMarine Ltd", "oemn:Var03", "ExpA_Ratio", "", "EAR", "prop:Propeller"],
    ["OEMN_OEM.ttl", "oemn", "PolarMarine Ltd", "oemn:Var04", "F_fwdBlade_kN", "unit:KiloN", "Ff_kN", "prop:Propeller"],
    ["OEMN_OEM.ttl", "oemn", "PolarMarine Ltd", "oemn:Var05", "CabTemp_degC", "unit:DEG", "", ""],

    # --- OEMO ---
    ["OEMO_OEM.ttl", "oemo", "Nordic Drives Inc", "oemo:Var01", "FiceImp_kN", "unit:KiloN", "Fti_kN", "prop:ThrusterSystem"],
    ["OEMO_OEM.ttl", "oemo", "Nordic Drives Inc", "oemo:Var02", "gear_reduct", "", "gearRatio", "comp:Gearbox"],
    ["OEMO_OEM.ttl", "oemo", "Nordic Drives Inc", "oemo:Var03", "K_torsNmPerRad", "", "torsionalStiffness_kNmPerRad", "comp:Coupling"],
    ["OEMO_OEM.ttl", "oemo", "Nordic Drives Inc", "oemo:Var04", "NoiseLevel_dB", "unit:HZ", "", ""],
    ["OEMO_OEM.ttl", "oemo", "Nordic Drives Inc", "oemo:Var05", "VendorRef", "", "", ""],
]

cols = ["oem_file", "namespace", "vendor", "original_var_iri", "original_name", "unit", "canonical_id", "domain"]

# load current mapping (back it up first)
df = pd.read_csv("master_mapping.csv")
df_new = pd.DataFrame(new_rows, columns=cols)

# append new rows
df_combined = pd.concat([df, df_new], ignore_index=True)
df_combined.to_csv("master_mapping.csv", index=False)

print(f"✅ Appended {len(new_rows)} new rows to master_mapping.csv. Total rows: {len(df_combined)}")
