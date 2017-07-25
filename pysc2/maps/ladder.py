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
"""Define the ladder map configs."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os


from pysc2.maps import lib


class Ladder(lib.Map):
  players = 2
  game_steps_per_episode = 16 * 60 * 30  # 30 minute limit.


ladder_base = "ladder"
ladder_seasons = [
    ("Ladder2016s6", os.path.join(ladder_base, "2016-S6")),
    ("Ladder2017s1", os.path.join(ladder_base, "2017-S1")),
    ("Ladder2017s2", os.path.join(ladder_base, "2017-S2")),
]

for name, directory in ladder_seasons:
  globals()[name] = type(name, (Ladder,), dict(directory=directory))


# pylint: disable=bad-whitespace, undefined-variable
ladder_maps = [
    ("AbyssalReef",          Ladder2017s2, "2-AbyssalReefLE"),
    ("AscensiontoAiur",      Ladder2017s2, "2-AscensiontoAiurLE"),
    ("BelShirVestige",       Ladder2017s1, "2-BelShirVestigeLE-Void"),
    ("BloodBoil",            Ladder2017s2, "2-BloodBoilLE"),
    ("CactusValley",         Ladder2017s1, "4-CactusValleyLE-Void"),
    ("Daybreak",             Ladder2016s6, "2-DaybreakLE-Void"),
    ("DefendersLanding",     Ladder2017s2, "2-DefendersLandingLE"),
    ("Echo",                 Ladder2016s6, "2-EchoLE-Void"),
    ("HabitationStation",    Ladder2016s6, "2-HabitationStationLE-Void"),
    ("Honorgrounds",         Ladder2017s1, "4-HonorgroundsLE"),
    ("NewkirkPrecinct16s6",  Ladder2016s6, "2-NewkirkPrecinctTE-Void"),
    ("NewkirkPrecinct",      Ladder2017s1, "2-NewkirkPrecinctTE-Void"),
    ("Odyssey",              Ladder2017s2, "2-OdysseyLE"),
    ("Overgrowth",           Ladder2016s6, "2-OvergrowthLE-Void"),
    ("PaladinoTerminal",     Ladder2017s1, "2-PaladinoTerminalLE"),
    ("ProximaStation",       Ladder2017s2, "2-ProximaStationLE"),
    ("Sequencer",            Ladder2017s2, "2-SequencerLE"),
    ("VaaniResearchStation", Ladder2016s6, "2-VaaniResearchStation-Void"),
    ("WhirlWind",            Ladder2016s6, "4-WhirlWindLE-Void"),
]
# pylint: enable=bad-whitespace, undefined-variable

# Create the classes dynamically, putting them into the module scope. They all
# inherit from a parent and set the players based on the map filename.
for name, parent, map_file in ladder_maps:
  globals()[name] = type(name, (parent,), dict(filename=map_file,
                                               players=int(map_file[0])))
