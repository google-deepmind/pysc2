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

import re

from pysc2.maps import lib


class Ladder(lib.Map):
  players = 2
  game_steps_per_episode = 16 * 60 * 30  # 30 minute limit.
  download = "https://github.com/Blizzard/s2client-proto#map-packs"


ladder_seasons = [
    "Ladder2017Season1",
    "Ladder2017Season2",
    "Ladder2017Season3",
    "Ladder2017Season4",
    "Ladder2018Season1",
    "Ladder2018Season2",
    "Ladder2018Season3",
    "Ladder2018Season4",
    "Ladder2019Season1",
    "Ladder2019Season2",
    "Ladder2019Season3",
]

for name in ladder_seasons:
  globals()[name] = type(name, (Ladder,), dict(directory=name))


# pylint: disable=bad-whitespace, undefined-variable
# pytype: disable=name-error
ladder_maps = [
    (Ladder2018Season2, "16-Bit LE", 2),
    (Ladder2018Season1, "Abiogenesis LE", 2),
    (Ladder2017Season4, "Abyssal Reef LE", 2),
    (Ladder2018Season3, "Acid Plant LE", 2),
    (Ladder2017Season3, "Acolyte LE", 2),
    (Ladder2019Season3, "Acropolis LE", 2),
    (Ladder2017Season4, "Ascension to Aiur LE", 2),
    (Ladder2019Season1, "Automaton LE", 2),
    (Ladder2018Season1, "Backwater LE", 2),
    (Ladder2017Season4, "Battle on the Boardwalk LE", 2),
    (Ladder2017Season1, "Bel'Shir Vestige LE", 2),
    (Ladder2017Season2, "Blood Boil LE", 2),
    (Ladder2018Season4, "Blueshift LE", 2),
    (Ladder2017Season1, "Cactus Valley LE", 4),
    (Ladder2018Season2, "Catalyst LE", 2),
    (Ladder2018Season4, "Cerulean Fall LE", 2),
    (Ladder2019Season2, "Cyber Forest LE", 2),
    (Ladder2018Season2, "Darkness Sanctuary LE", 4),
    (Ladder2017Season2, "Defender's Landing LE", 2),
    (Ladder2019Season3, "Disco Bloodbath LE", 2),
    (Ladder2018Season3, "Dreamcatcher LE", 2),
    (Ladder2018Season1, "Eastwatch LE", 2),
    (Ladder2019Season3, "Ephemeron LE", 2),
    (Ladder2018Season3, "Fracture LE", 2),
    (Ladder2017Season3, "Frost LE", 2),
    (Ladder2017Season1, "Honorgrounds LE", 4),
    (Ladder2017Season3, "Interloper LE", 2),
    (Ladder2019Season2, "Kairos Junction LE", 2),
    (Ladder2019Season2, "King's Cove LE", 2),
    (Ladder2018Season3, "Lost and Found LE", 2),
    (Ladder2017Season3, "Mech Depot LE", 2),
    (Ladder2018Season1, "Neon Violet Square LE", 2),
    (Ladder2019Season2, "New Repugnancy LE", 2),
    (Ladder2017Season1, "Newkirk Precinct TE", 2),
    (Ladder2017Season4, "Odyssey LE", 2),
    (Ladder2017Season1, "Paladino Terminal LE", 2),
    (Ladder2018Season4, "Para Site LE", 2),
    (Ladder2019Season1, "Port Aleksander LE", 2),
    (Ladder2017Season2, "Proxima Station LE", 2),
    (Ladder2018Season2, "Redshift LE", 2),
    (Ladder2017Season2, "Sequencer LE", 2),
    (Ladder2018Season4, "Stasis LE", 2),
    (Ladder2019Season3, "Thunderbird LE", 2),
    (Ladder2019Season3, "Triton LE", 2),
    (Ladder2019Season2, "Turbo Cruise '84 LE", 2),
    (Ladder2019Season3, "Winter's Gate LE", 2),
    (Ladder2019Season3, "World of Sleepers LE", 2),
    (Ladder2019Season1, "Year Zero LE", 2),

    # Disabled due to being renamed to Neo Seoul
    # (Ladder2018Season1, "Blackpink LE", 2),
]
# pylint: enable=bad-whitespace, undefined-variable
# pytype: enable=name-error

# Create the classes dynamically, putting them into the module scope. They all
# inherit from a parent and set the players based on the map filename.
for parent, bnet, players in ladder_maps:
  name = re.sub(r"[ '-]|[LTRS]E$", "", bnet)
  map_file = re.sub(r"[ ']", "", bnet)
  globals()[name] = type(name, (parent,), dict(
      filename=map_file, players=players, battle_net=bnet))

