# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Define the static list of units for SC2."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# pylint: disable=line-too-long
class Terran(enum.IntEnum):
    Armory = 29
    AutoTurret = 31
    Banshee = 55
    Barracks = 21
    BarracksFlying = 46
    BarracksReactor = 38
    BarracksTechLab = 37
    Battlecruiser = 57
    Bunker = 24
    CommandCenter = 18
    CommandCenterFlying = 36
    Cyclone = 692
    EngineeringBay = 22
    Factory = 27
    FactoryFlying = 43
    FactoryReactor = 40
    FactoryTechLab = 39
    FusionCore = 30
    Ghost = 50
    GhostAcademy = 26
    Hellion = 53
    HellionTank = 484
    KD8Charge = 830
    Liberator = 689
    LiberatorAG = 734
    MULE = 268
    Marauder = 51
    Marine = 48
    Medivac = 54
    MissileTurret = 23
    Nuke = 58
    OrbitalCommand = 132
    OrbitalCommandFlying = 134
    PlanetaryFortress = 130
    PointDefenseDrone = 11
    Raven = 56
    Reactor = 6
    Reaper = 49
    Refinery = 20
    SCV = 45
    SensorTower = 25
    SiegeTank = 33
    SiegeTankSieged = 32
    Starport = 28
    StarportFlying = 44
    StarportReactor = 42
    StarportTechLab = 41
    SupplyDepot = 19
    SupplyDepotLowered = 47
    TechLab = 5
    Thor = 52
    ThorAP = 691
    VikingAssault = 34
    VikingFighter = 35
    WidowMine = 498
    WidowMineBurrowed = 500

class Zerg(enum.IntEnum):
    Baneling = 9
    BanelingBurrowed = 115
    BanelingCocoon = 8
    BanelingNest = 96
    BroodLord = 114
    BroodLordCocoon = 113
    Broodling = 289
    Changeling = 12
    ChangelingMarine = 15
    ChangelingMarineShield = 14
    ChangelingZealot = 13
    ChangelingZergling = 17
    ChangelingZerglingWings = 16
    Corruptor = 112
    CreepTumor = 87
    CreepTumorBurrowed = 137
    CreepTumorQueen = 138
    Drone = 104
    DroneBurrowed = 116
    Egg = 103
    EvolutionChamber = 90
    Extractor = 88
    GreaterSpire = 102
    Hatchery = 86
    Hive = 101
    Hydralisk = 107
    HydraliskBurrowed = 117
    HydraliskDen = 91
    InfestationPit = 94
    InfestedTerransEgg = 150
    Infestor = 111
    InfestorBurrowed = 127
    InfestorTerran = 7
    Lair = 100
    Larva = 151
    LocustMP = 489
    LocustMPFlying = 693
    LurkerDenMP = 504
    LurkerMP = 502
    LurkerMPBurrowed = 503
    LurkerMPEgg = 501
    Mutalisk = 108
    NydusCanal = 142
    NydusNetwork = 95
    Overlord = 106
    OverlordCocoon = 128
    OverlordTransport = 893
    Overseer = 129
    ParasiticBombDummy = 824
    Queen = 126
    QueenBurrowed = 125
    Ravager = 688
    RavagerCocoon = 687
    Roach = 110
    RoachBurrowed = 118
    RoachWarren = 97
    SpawningPool = 89
    SpineCrawler = 98
    SpineCrawlerUprooted = 139
    Spire = 92
    SporeCrawler = 99
    SporeCrawlerUprooted = 140
    SwarmHostBurrowedMP = 493
    SwarmHostMP = 494
    TransportOverlordCocoon = 892
    Ultralisk = 109
    UltraliskCavern = 93
    Viper = 499
    Zergling = 105
    ZerglingBurrowed = 119

class Protoss(enum.IntEnum):
    Adept = 311
    AdeptPhaseShift = 801
    Archon = 141
    Assimilator = 61
    Carrier = 79
    Colossus = 4
    CyberneticsCore = 72
    DarkShrine = 69
    DarkTemplar = 76
    Disruptor = 694
    DisruptorPhased = 733
    FleetBeacon = 64
    Forge = 63
    Gateway = 62
    HighTemplar = 75
    Immortal = 83
    Interceptor = 85
    Mothership = 10
    MothershipCore = 488
    Nexus = 59
    Observer = 82
    Oracle = 495
    OracleStasisTrap = 732
    Phoenix = 78
    PhotonCannon = 66
    Probe = 84
    Pylon = 60
    PylonOvercharged = 894
    RoboticsBay = 70
    RoboticsFacility = 71
    Sentry = 77
    Stalker = 74
    Stargate = 67
    Tempest = 496
    TemplarArchive = 68
    TwilightCouncil = 65
    VoidRay = 80
    WarpGate = 133
    WarpPrism = 81
    WarpPrismPhasing = 136
    Zealot = 73

class Neutral(enum.IntEnum):
    BattleStationMineralField = 886
    BattleStationMineralField750 = 887
    CollapsibleRockTowerDebris = 490
    CollapsibleRockTowerDiagonal = 588
    CollapsibleRockTowerPushUnit = 561
    CollapsibleTerranTowerDebris = 485
    CollapsibleTerranTowerDiagonal = 589
    CollapsibleTerranTowerPushUnit = 562
    CollapsibleTerranTowerPushUnitRampLeft = 559
    CollapsibleTerranTowerPushUnitRampRight = 560
    CollapsibleTerranTowerRampLeft = 590
    CollapsibleTerranTowerRampRight = 591
    DebrisRampLeft = 486
    DebrisRampRight = 487
    DestructibleDebris6x6 = 365
    DestructibleDebrisRampDiagonalHugeBLUR = 377
    DestructibleDebrisRampDiagonalHugeULBR = 376
    DestructibleRock6x6 = 371
    DestructibleRockEx1DiagonalHugeBLUR = 641
    ForceField = 135
    KarakFemale = 324
    LabMineralField = 665
    LabMineralField750 = 666
    MineralField = 341
    MineralField750 = 483
    ProtossVespeneGeyser = 608
    PurifierMineralField = 884
    PurifierMineralField750 = 885
    PurifierRichMineralField = 796
    PurifierRichMineralField750 = 797
    PurifierVespeneGeyser = 880
    RichMineralField = 146
    RichMineralField750 = 147
    RichVespeneGeyser = 344
    Scantipede = 335
    ShakurasVespeneGeyser = 881
    SpacePlatformGeyser = 343
    UnbuildableBricksDestructible = 473
    UnbuildablePlatesDestructible = 474
    UtilityBot = 330
    VespeneGeyser = 342
    XelNagaTower = 149
# pylint: enable=line-too-long
