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
"""Define the ladder map configs.

Refer to the map descriptions here:
http://wiki.teamliquid.net/starcraft2/Maps/Ladder_Maps/Legacy_of_the_Void
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pysc2.maps import lib


class Ladder(lib.Map):
  players = 2
  game_steps_per_episode = 16 * 60 * 30  # 30 minute limit.
  download = "https://github.com/Blizzard/s2client-proto#map-packs"


ladder_seasons = [
    "Ladder2017Season1",
    "Ladder2017Season2",
    "Ladder2017Season3",
]

for name in ladder_seasons:
  globals()[name] = type(name, (Ladder,), dict(directory=name))


# pylint: disable=bad-whitespace, undefined-variable
ladder_maps = [
    ("AbyssalReef",          Ladder2017Season3, "AbyssalReefLE", 2),
    ("Acolyte",              Ladder2017Season3, "AcolyteLE", 2),
    ("AscensiontoAiur",      Ladder2017Season3, "AscensiontoAiurLE", 2),
    ("BelShirVestige",       Ladder2017Season1, "BelShirVestigeLE", 2),
    ("BloodBoil",            Ladder2017Season2, "BloodBoilLE", 2),
    ("CactusValley",         Ladder2017Season1, "CactusValleyLE", 4),
    ("DefendersLanding",     Ladder2017Season2, "DefendersLandingLE", 2),
    ("Frost",                Ladder2017Season3, "FrostLE", 2),
    ("Honorgrounds",         Ladder2017Season1, "HonorgroundsLE", 4),
    ("Interloper",           Ladder2017Season3, "InterloperLE", 2),
    ("MechDepot",            Ladder2017Season3, "MechDepotLE", 2),
    ("NewkirkPrecinct",      Ladder2017Season1, "NewkirkPrecinctTE", 2),
    ("Odyssey",              Ladder2017Season3, "OdysseyLE", 2),
    ("PaladinoTerminal",     Ladder2017Season1, "PaladinoTerminalLE", 2),
    ("ProximaStation",       Ladder2017Season2, "ProximaStationLE", 2),
    ("Sequencer",            Ladder2017Season2, "SequencerLE", 2),
]
# pylint: enable=bad-whitespace, undefined-variable

# Create the classes dynamically, putting them into the module scope. They all
# inherit from a parent and set the players based on the map filename.
for name, parent, map_file, players in ladder_maps:
  globals()[name] = type(name, (parent,), dict(filename=map_file,
                                               players=players))

