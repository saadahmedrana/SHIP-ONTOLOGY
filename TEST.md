Conventions:
  UnitsObject: '{ "value": <number>, "unit": "<unit>" }'
  CommonUnits:
    length: [m, mm]
    area: [m²]
    angle: [deg]
    speed: [rpm, 'rev/s', kn]
    force: [kN]
    torque: [kNm]
    pressure: [bar]
    volume: [m³]
    time: [h]
    energy: [kJ]
  CardinalityLegend:
    '1..1': exactly one
    '0..1': optional (≤1)
    '1..*': one or more
    '0..*': zero or more

Enums:
  IceClass: [IASuper, IA, IB, IC, II, III]
  PropulsorArrangement: [singleScrew, twinScrew, tripleScrew]
  PrimeMoverType: [twoStrokeDiesel, fourStrokeDiesel, dualFuelEngine, gasEngine, gasTurbine, steamTurbine, electricMotor]
  StartingMethod: [airStart, electricStart, hydraulicStart]
  FuelKind: [HFO, MDO, MGO, LNG, methanol, other]
  CoolingCircuit: [seaWaterOpenLoop, freshWaterClosedLoop]
  PropellerType: [open, ducted]
  PitchType: [FP, CP]
  ThrusterType: [azimuthingZDrive, azimuthingLDrive, podded, rimDriven]
  ThrusterMode: [pushing, pulling]
  BearingType: [thrust, sternTubeAft, sternTubeFwd, lineBearing]
  SealType: [simpleLip, doubleLip, faceSeal]
  CouplingType: [rigid, flexible, clutch]
  MaterialKind: [bronze, austeniticSteel, nodularCastIron, steel, aluminium, composite]
  SNcurveType: [twoSlope, oneSlope]
  AnalysisMethod: [timeDomain, frequencyDomain]
  HullRegion: [Bow, Midbody, Stern]
  SpecialStrengthZones: [UpperBowIceBeltRegion, ForefootRegion]
  Orientation: [longitudinal, transverse]
  SupportType: [deck, stringer, bulkhead, tankTop, webFrame]


ObjectProperties:
  hasSystem:         { domain: Ship, range: System, cardinality: '0..*' }
  hasEquipment:      { domain: System, range: Equipment, cardinality: '0..*' }
  hasComponent:      { domain: Equipment, range: Component, cardinality: '0..*' }
  hasSubcomponent:   { domain: Component, range: Component, cardinality: '0..*' }
  hasClearanceFor:
        domain: SternStructure
        range: PropulsorSystem
        cardinality: '0..*'
        notes: 'Used by SHACL to enforce sternClearance ≥ propellerSubmersionDepth_h0.'




  # Propulsion decomposition
  hasPropulsor:      { domain: PropulsionSystem, range: [PropulsorSystem, ThrusterSystem], cardinality: '1..1', notes: 'XOR' }
  hasShaftingSystem:      { domain: PropulsionSystem, range: ShaftingSystem, cardinality: '1..1' }
  hasGearbox:        { domain: PropulsionSystem, range: Gearbox, cardinality: '0..1' }
  hasCoupling:       { domain: PropulsionSystem, range: Coupling, cardinality: '1..*' }
  hasControlAndMonitoring: { domain: PropulsionSystem, range: ControlAndMonitoringSystem, cardinality: '0..1' }

  # Cross-links & placement
  isConnectedTo:     { domain: PrimeMover, range: ShaftingSystem, cardinality: '1..1' }
  servesEngine:      { domain: [CoolingWaterSystem, StartingSystem, FuelSystem, LubricatingOilSystem], range: PrimeMover, cardinality: '1..*' }

  # Materials / location / attachment
  hasMaterial:       { domain: [Propeller, Nozzle, AzimuthingThruster, SternTubeAssembly, ShaftSeals], range: MaterialKind, cardinality: '1..1' }
  locatedInHullRegion: { domain: StructuralElement, range: [HullRegion, SpecialStrengthZones], cardinality: '0..*' }
  isAttachedTo:      { domain: StructuralElement, range: SupportingElement, cardinality: '0..*' }



Ship (root):
  data: { iceClass: IceClass, serviceSpeed: { kn: 0 } }
  hasSystem:
    - HullStructureSystem (1..1)
    - PropulsionSystem (1..1)
    - ElectricalPowerSystem (0..1)
    - SteeringAndManeuveringSystem (0..1)
    - NavigationCommunicationControlSystem (0..1)
    - SafetySystem (0..1)
    - EnvironmentSystem (0..1)
    - CargoHandlingSystem (0..1)
    - HVACandAccommodationSystem (0..1)



HullStructureSystem (System):
  Equipment:
    - ShipHullStructure
      Components:
        - Keel
        - BottomStructure
          Subcomponents: [InnerBottom, BottomPlating, Floors, Longitudinals, Girders]
        Sides:
            SidePlate:
                data:
                thickness: { mm: 0 }
                iceBeltVerticalExtentTop: { m: 0 }
                iceBeltVerticalExtentBottom: { m: 0 }
            Frames:
                TransverseFrame:
                data:
                    span: { m: 0 }
                    spacing: { m: 0 }
                    sectionModulusZ: { cm³: 0 }   # §4.5
                    shearAreaA: { cm²: 0 }        # §4.5
                LongitudinalFrame:
                data:
                    span: { m: 0 }
                    spacing: { m: 0 }
                    sectionModulusZ: { cm³: 0 }
                    shearAreaA: { cm²: 0 }
            WebFrames:
                data:
                spacing: { m: 0 }
                sectionModulusZ: { cm³: 0 }     # §4.6
                shearAreaA: { cm²: 0 }
            IceStringers:
                data:
                spacing: { m: 0 }
                sectionModulusZ: { cm³: 0 }
                shearAreaA: { cm²: 0 }

        - DeckStructure
          Subcomponents: [MainDeck, UpperDecks, DeckGirders, Beams]
        - Bulkheads
          Subcomponents: [TransverseBulkheads, LongitudinalBulkheads, WatertightDoors]
          - BowStructure
          data:
            LBOW: { "value": 0, "unit": "m" }
            Awf: { "value": 0, "unit": "m²" }
            alpha: { "value": 0, "unit": "deg" }
          subassemblies:
            StemAndGeometry:
              data:
                phi1: { "value": 0, "unit": "deg" }
                phi2: { "value": 0, "unit": "deg" }
                psi: { "value": 0, "unit": "deg" }
                stemConstructionType: "rolled|cast|forged|plate"
            BulbousBow:
              data:
                hasBulbousBow: false
            UpperBowIceBeltRegion: {}
            ForefootRegion: {}
          Subcomponents: [Stem, Forefoot, BulbousBow]
        - SternStructure
          Subcomponents: [SternFrame, AftDeadwood, Skeg, ShaftBossings]
        - Superstructure
        - FoundationsAndChocks
        - MarkingsOnStructure
        - CoatingsAndCathodicProtection


            ShipHullStructure:
            data:
                L: { m: 0 }
                LBOW: { m: 0 }
                LPAR: { m: 0 }
                B: { m: 0 }
                T: { m: 0 }         # ice-class draught at UIWL/LIWL context
                UIWL: { m: 0 }
                LIWL: { m: 0 }
                Awf: { m²: 0 }      # bow waterline area
                alpha: { deg: 0 }   # waterline angle at B/4
                phi1: { deg: 0 }    # stem rake
                phi2: { deg: 0 }    # bow rake at B/4
                psi: { deg: 0 }     # flare angle (derived if needed)
                DP: { m: 0 }        # propeller diameter reference
                HM: { m: 0 }
                HF: { m: 0 }        # brash ice thicknesses
                delta: { t: 0 }     # displacement
            SternStructure:
                data:
                sternClearance: { m: 0 }  # must be ≥ propellerSubmersionDepth_h0



PropulsionSystem (System):   # Overview; detailed parameters below
  data: { iceClass: IceClass, propulsorArrangement: PropulsorArrangement }
  hasPropulsor: [PropulsorSystem, ThrusterSystem]  # XOR
  hasShaftingSystem: ShaftingSystem
  hasGearbox: Gearbox (0..1)
  hasCoupling: Coupling (1..*)
  Equipment:
    - PrimeMover (Engine)
      Subsystems:
        - FuelSystem
        - StartingSystem
        - CoolingWaterSystem
        - LubricatingOilSystem
        - IntakeAndExhaustSystem
        - ControlAndMonitoringSystem
        - Governor (TBD)
        - Turbocharger (TBD)
    - TransmissionSystem
      Components: [Gearbox, Coupling]
    - ShaftingSystem
      Components:
        - IntermediateShaft (1.*)
        - SternTubeAssembly
          Subcomponents: [AftBearing, FwdBearing, Liner, StuffingBox (if any)]
        - ShaftSeals (0.*)
        - Bearings (thrust/sternTube/line)
        - ShaftBrakes (optional)
        - TorsionalVibrationDamper (optional)
    - PropulsorSystem (XOR with ThrusterSystem)
      Components: [Propeller, Nozzle (optional), HubAndCPMechanism (optional)]
    - ThrusterSystem (XOR with PropulsorSystem)
      Components:
        - AzimuthingThruster
          Subcomponents: [Pod/Leg, SlewBearing, SteeringActuators, Propeller, Nozzle (optional)]
    - ControlAndMonitoringSystem (optional)
    AlternativeDesignStudy:
        applied: false
        method: "FEM"    # FEM | modelTest | CFD
        coversFatigue: false
        coversVibration: false
        coversExtremeLoads: false
        reportReference: "TBD"





PrimeMover:
  data:
    primeMoverType: PrimeMoverType
    mcrPower: { kW: 0 }
    mcrRpm: { rpm: 0 }       
    reversible: false
    qEmax: { kNm: 0 }        # defaults allowed per rules
    inertiaRatio_Ie_It: 0
    requiresBladeOrderResonanceAssessment: false
  starting:                   # TRAFICOM §7.1
    startingMethod: StartingMethod
    airReceiverCapacity: { 'Nm³@pressure': 0 }   # ≥12 starts if reversible, ≥6 if not
    compressorChargeTime: { h: 0 }               # ≤0.5 h IASuper & reversible; else ≤1 h
  cooling:                    # TRAFICOM §7.2
    seaChestVolume: { m³: 0 }                    # ≈ 1 m³ per 750 kW total engine output
    strainerOpenAreaRatio: 0                     # ≥ 4
    dischargeRecirculationProvided: true
    locationNearCenterlineAft: true
    iceAccumulationHeadroom: true
  fuel:
    deliveredViscosity: 'cSt@°C'
    heaterSurfaceTempLimit: { '°C': 0 }
    boosterFlowCapacityAt120pct: { 'kg/h': 0 }
    samplingPoints: { beforeSeparator: true, afterSeparator: true }
    viscosityControllerParams: { setpoint_cSt_at_°C: 0 }
    heaterRedundancy: true
  links:
    isConnectedTo: ShaftingSystem




TransmissionSystem:
  data:
    inertiaRatio_Ie_It: 0
    torsionalStiffness: { 'kNm/rad': 0 }
  hasComponent:
    Gearbox:
      data:
        gearRatio: 0
        ratedTorque: { kNm: 0 }
        torsionalStiffness: { 'kNm/rad': 0 }
        efficiency: 0
    Coupling:
      data:
        couplingType: CouplingType
        ratedTorque: { kNm: 0 }
        maxMisalignment: { mrad: 0 }




ShaftingSystem:
  hasComponent:
    IntermediateShaft: {}
    SternTubeAssembly:
      data: { length: { m: 0 }, diameter: { m: 0 }, linerMaterial: MaterialKind }
    ShaftSeals:
      data: { sealType: SealType, designPressure: { bar: 0 }, redundancy: true }
    Bearings:
      data:
        bearingType: BearingType
        ratedLoad: { "value": 0, "unit": "kN" }
        allowableContactPressure: { MPa: 0 }
        fatigueSafetyFactor: 1.5
        cooling: 'string'
    ShaftBrakes: {}                # §6.6.4 braking check
    TorsionalVibrationDamper: {}   # §6.5.3 resonance control
    data:
        Qr: { kNm: 0 }     # design response torque
        Tr: { kN: 0 }      # design response thrust
        resonanceWithin20pctOfMaxSpeed: false
        hasFirstBladeOrderResonance: false
        analysisMethod: AnalysisMethod
        safetyFactorExtremeYield: 1.3
        safetyFactorFatigue: 1.5
        safetyFactorBladeFailureYield: 1.0




PropulsorSystem:
  hasComponent:
    Propeller:
      data:
        propellerType: PropellerType
        pitchType: PitchType
        material: MaterialKind
        operationType: "channel"   # channel | ramming (§6.3, design operation type)
        # geometry & operation
        hubDiameter_d: { m: 0 }
        nn: { "value": 0, "unit": "rpm" }, n_bollard: { "value": 0, "unit": "rpm"}, serviceSpeed: { "value": 0, "unit": "kn" }
        skewAt0_7R: { "value": 0, "unit": "deg" }
        rakeAt0_7R: { "value": 0, "unit": "deg" }
        fatigueReductions: { gamma_eps1: 0.67, gamma_eps2: 0.67, gamma_n: 0.75, gamma_m: 0.75 }
        # immersion & factors
        propellerSubmersionDepth_h0: { m: 0 }
        k1: 0, k2: 0, k3: 0
        fImmersion: { params: ['h0','Cice','D'] }
        # ice loads & torsion (TRAFICOM §6.5)
        Fb: { kN: 0 }, Ff: { kN: 0 }, Qsmax: { kNm: 0 }
        loadedArea: { m²: 0 }, loadDistribution: 'reference'
        Tb: { kN: 0 }, Tf: { kN: 0 }, Qmax: { kNm: 0 }, n_limit: { rpm: 0 }
        Nice: 0
        # blade failure & fatigue
        Fex: { kN: 0 }, Qsex: { kNm: 0 }
          fatigueSN:
            snCurveType: SNcurveType      # oneSlope | twoSlope
            openPropellerParams:
                B1: 0
                B2: 0
                B3: 0
                C1: 0
                C2: 0
                C3: 0
                C4: 0
            ductedPropellerParams:
                B1: 0
                B2: 0
                B3: 0
                C1: 0
                C2: 0
                C3: 0
                C4: 0

        rho: 0.0
        materialFatigueParams:
            sigma_fL: { "value": 0, "unit": "MPa" }
            sigmaRef1: { "value": 0, "unit": "MPa" }   # reference stress 1 (§6.6.2.3)
            sigmaRef2: { "value": 0, "unit": "MPa" }   # reference stress 2 (§6.6.2.3)
            slopes: "string"
            reductions:
                gamma_eps1: 0.67
                gamma_eps2: 0.67
                gamma_n: 0.75
                gamma_m: 0.75
    Nozzle:
      data:
        nozzleType: 'string'  # e.g. 19A, 37
        lipThickness: { mm: 0 }
        inletRadius: { mm: 0 }
        throatDiameter: { m: 0 }
        length: { m: 0 }
        material: MaterialKind
    HubAndCPMechanism:
      data:
        maxBladeAngle: { deg: 0 }
        minBladeAngle: { deg: 0 }
        actuationPressure: { bar: 0 }
        boltDesignForFex: true



ThrusterSystem:
  hasComponent:
    AzimuthingThruster:
      data:
            thrusterType: ThrusterType
            thrusterMode: ThrusterMode
            projectedAreaAt: { m²: 0 }
            stemToHullClearance: { m: 0 }
            Hiced: { m: 0 }, hi: { m: 0 }
            locationFactor_k1: 0
            designOperationSpeedInIce: { 'm/s': 0 }
            impactSphereRadius_Rc: { m: 0 }
            ridgePenetration:
                Ftr: { value: 0, unit: "kN" }
                Hr: { value: 0, unit: "m" }        # ridge thickness
                At: { value: 0, unit: "m²" }       # vertical projected area
                contactAreaLimitedByHr: true       # §6.6.5.3, formula 6.48
            naturalFrequencyRange: { Hz: 0 }
            attachmentStiffness: { 'kN/m': 0 }
            globalVibrationCheck: true
            reuse: 'Propeller geometry/loads where applicable'
        Subcomponents:
            - Pod
            - Leg
            - SlewBearing
            - SteeringActuators



RudderAndSteeringSystem:
    rudderDesignSpeedMinima:
        IASuper: { "value": 20, "unit": "kn" }
        IA: { "value": 18, "unit": "kn" }
        IB: { "value": 16, "unit": "kn" }
        IC: { "value": 14, "unit": "kn" }


ControlAndMonitoringSystem:
  data:
    torsionalVibrationMonitoring: false
    bladeLoadMonitoring: false
  MonitoringEvent:
    data:
      timestamp: 'ISO-8601'
      variableName: 'Qr|Tr|Qmax|Fb|...'
      measuredValue: { value: 0, unit: 'kNm|kN|...' }
      threshold: { value: 0, unit: 'same' }
      exceeded: false


FuelSystem:
  Subcomponents:
    - StorageTanks
    - DayTank
    - TransferPumps
    - CentrifugalSeparators
    - BoosterSystem
    - FuelHeaters
    - ViscosityController
    - Filters
    - FuelMeters

LubricatingOilSystem:
  Subcomponents:
    - LOPump
    - LOCooler
    - LOFilter
  data:
    pumpRedundancy: true
    oilTemperatureRange: { "min": 0, "max": 0, "unit": "°C" }
IntakeAndExhaustSystem:
  Subcomponents:
    - AirIntakeFilters
    - Turbocharger (if applicable)
    - ExhaustManifold
    - Silencer
  data:
    designBackPressure: { "value": 0, "unit": "bar" }
    turbochargerIncluded: false


ElectricalPowerSystem (System):
  Equipment:
    - Generators (Main, Emergency)
    - MainSwitchboard
    - DistributionPanels
    - Converters/Drives (VFDs)
    - UPS
    - CablesAndTrunking
    - EmergencyPowerSource

SteeringAndManeuveringSystem (System):
  Equipment:
    - RudderAndSteeringSystem
      Components: [Rudder, Stock, Pintles, Bearings, SteeringGear, Telemotor, Feedback]
    - BowThrusters (Manoeuvring)
    - SternThrusters (Manoeuvring)

NavigationCommunicationControlSystem (System):
  Equipment:
    - NavigationSuite (Radar, ECDIS, Gyro, Log, EchoSounder)
    - CommunicationSuite (GMDSS, VHF)
    - ControlConsoles
    - SensorsAndReference (MRU, GPS, PRS)

SafetySystem (System):
  Equipment:
    - FireDetectionAndAlarm
    - FixedFireExtinguishing
    - PortableExtinguishers
    - FloodingDetection
    - WatertightDoorsControl

EnvironmentSystem (System):
  Equipment:
    - BilgeAndBallast
    - SewageTreatment
    - OilyWaterSeparation
    - EmissionsControl (SCR/EGR)

CargoHandlingSystem (System):
  Equipment:
    - CargoPumps
    - CargoPipelines
    - Cranes/Hoists
    - HatchCovers

HVACandAccommodationSystem (System):
  Equipment:
    - AirHandlingUnits
    - ChilledWaterSystem
    - VentilationDucts
    - AccommodationOutfitting



MaterialsRequirements:
  seawaterExposedPropulsorParts:
    elongation: '>= 15% (GL=5·D specimen)'
    charpyV:
      general: '>= 20 J @ -10°C'
      nodularCastIron: '>= 10 J @ -10°C'
      exemptions: [bronze, austeniticSteel]
  shaftAndPropellerSteels:
    yieldStrength: { "value": 0, "unit": "MPa" }   # σ0.2
    tensileStrength: { "value": 0, "unit": "MPa" } # σu


RegulatoryVariablesCatalogue:
  ShipHull:
    - L; LBOW; LPAR; B; T; UIWL; LIWL; Awf; alpha; phi1; phi2; DP; delta; HM; HF
  PropellerOperation:
    - D; Z; P0_7; c0_7; EAR; hubDiameter_d; nn; n_bollard; serviceSpeed
  IceFactorsAndLoads:
    - Hice; Hiced; Hr; Nclass; Nice; k1; k2; k3; fImmersion; designOperationSpeedInIce; impactSphereRadius_Rc
  EngineAndResponse:
    - Ke; RCH; Qemax; Qmax; Qr; Tr; n_limit; isResonantCase; analysisMethod; inertiaRatio_Ie_It
  Steering:
    - rudderDesignSpeed
  IceFactorsAndLoads:
    - Hr   # ridge thickness, thrusters §6.6.5





ConstraintIntents:
  - PropellerIceTorque_OpenVsDucted: "Qmax via open/ducted formulas; n_limit switch; allow defaults for n_bollard."
  - AxialDesignLoads: "Compute Tb/Tf; derive Tr for shaft sizing."
  - BladeLoadsAndCounts: "Fb/Ff/Qsmax; Nice = k1*k2*k3*Nclass; ×Z when all blades act."
  - ShaftingSystemSafetyFactors: "extremeYield ≥1.3; fatigue ≥1.5; bladeFailureYield ≥1.0."
  - ResonanceMethodSelection: "If resonanceWithin20pctOfMaxSpeed=true ⇒ analysisMethod ∈ {timeDomain, frequencyDomain}; else non-resonant with Ie/It."
  - CPBossingIntegrity: "If pitchType=CP ⇒ boltDesignForFex=true; check hub/bossing/shaft vs Fex/Qsex."
  - ThrusterExtremesAndVibration: "Compute Fti/Ftr (T4/T5); limit vertical contact area by Hr; globalVibrationCheck=true; include added mass/damping & attachment stiffness."
  - PropellerImmersionAndLocation: "k2 from f(h0,Cice,D); k1 by location; k3 by machinery type; warn if highest point < hi (stricter class)."
  - SternHullClearance: "sternClearance ≥ propellerSubmersionDepth_h0."
  - RudderDesignSpeedMinima: "Meet class minima or actual if higher."
  - StartingAirCapacityAndCharge: "≥12 starts (reversible) / ≥6 (non-rev); charge ≤0.5 h IASuper & reversible, else ≤1 h."
  - CoolingSeaChestSizing: "≈1 m³/750 kW; strainer ≥4; recirc, near CL aft, headroom for ice."
  - DefaultQemaxWhenUnknown: "Set per rules table by prime mover/propulsor type."
  - name: PropellerBladeStressAcceptance
    idea: 'Check stresses under Fb/Ff/Qsmax with allowable stress; fatigue S–N curve at 1e8 cycles.'
  - name: PropellerFatigueAcceptance
    idea: 'σfatigue/σallowable ≥ 1.5; apply rho and fatigue reduction factors.'
  - name: ThrusterPlasticBendingAcceptance
    idea: 'Ensure plastic bending of a blade does not damage thruster body/hub.'
  - name: FuelTreatmentPerformance
    idea: 'Fuel system shall ensure proper viscosity, heater redundancy, sampling before/after separators, PI viscosity control.'



