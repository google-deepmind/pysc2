# Copyright 2021 DeepMind Technologies Ltd. All rights reserved.
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

from absl import flags
from absl.testing import absltest
from pysc2.lib.replay import sc2_replay

from pysc2.lib import gfile
from pysc2.lib import resources

FLAGS = flags.FLAGS
PATH = "pysc2/lib/replay/test_data/replay_01.SC2Replay"


class Sc2ReplayTest(absltest.TestCase):

  def setUp(self):
    super(Sc2ReplayTest, self).setUp()

    replay_path = resources.GetResourceFilename(PATH)
    with gfile.Open(replay_path, mode="rb") as f:
      replay_data = f.read()
    self._replay = sc2_replay.SC2Replay(replay_data)

  def testDetails(self):
    replay_details = self._replay.details()
    self.assertEmpty(replay_details["m_cacheHandles"])
    self.assertEqual(replay_details["m_campaignIndex"], 0)
    self.assertEqual(replay_details["m_defaultDifficulty"], 3)
    self.assertEqual(replay_details["m_description"], "")
    self.assertEqual(replay_details["m_difficulty"], "")
    self.assertFalse(replay_details["m_disableRecoverGame"])
    self.assertEqual(replay_details["m_gameSpeed"], 4)
    self.assertEqual(replay_details["m_imageFilePath"], "")
    self.assertFalse(replay_details["m_isBlizzardMap"])
    self.assertEqual(
        replay_details["m_mapFileName"],
        "Ladder2019Season1May/CyberForestLE.SC2Map")
    self.assertFalse(replay_details["m_miniSave"])
    self.assertEqual(
        replay_details["m_modPaths"], [
            "Mods/Liberty.SC2Mod",
            "Mods/Swarm.SC2Mod",
            "Mods/Void.SC2Mod",
            "Mods/VoidMulti.SC2Mod"
        ])
    # (there is more data here, just listing the most interesting bits)
    self.assertEqual(replay_details["m_playerList"][0]["m_name"], "Supervised")
    self.assertFalse(replay_details["m_playerList"][0]["m_observe"])
    self.assertEqual(replay_details["m_playerList"][0]["m_race"], "Protoss")
    self.assertEqual(replay_details["m_playerList"][0]["m_result"], 2)
    self.assertEqual(replay_details["m_playerList"][1]["m_name"],
                     "temp_x1_5_beast3f_6571236_final")
    self.assertFalse(replay_details["m_playerList"][1]["m_observe"])
    self.assertEqual(replay_details["m_playerList"][1]["m_race"], "Protoss")
    self.assertEqual(replay_details["m_playerList"][1]["m_result"], 1)
    self.assertFalse(replay_details["m_restartAsTransitionMap"])
    self.assertEqual(replay_details["m_thumbnail"]["m_file"], "Minimap.tga")
    self.assertEqual(replay_details["m_timeLocalOffset"], 0)
    self.assertEqual(replay_details["m_timeUTC"], 132772394814660570)
    self.assertEqual(replay_details["m_title"], "Cyber Forest LE")

  def testInitData(self):
    init_data = self._replay.init_data()
    # (there is more data here, just listing the most interesting bits)
    game_description = init_data["m_syncLobbyState"]["m_gameDescription"]
    self.assertEqual(game_description["m_gameOptions"]["m_fog"], 0)
    self.assertEqual(game_description["m_gameSpeed"], 4)
    self.assertEqual(game_description["m_isBlizzardMap"], False)
    self.assertEqual(game_description["m_isRealtimeMode"], False)
    self.assertEqual(
        game_description["m_mapFileName"],
        "Ladder2019Season1May/CyberForestLE.SC2Map")

  def testTrackerEvents(self):
    events = list(self._replay.tracker_events())
    event_types = set(s["_event"] for s in events)

    self.assertEqual(
        event_types,
        {"NNet.Replay.Tracker.SPlayerSetupEvent",
         "NNet.Replay.Tracker.SPlayerStatsEvent",
         "NNet.Replay.Tracker.SUnitBornEvent",
         "NNet.Replay.Tracker.SUnitDiedEvent",
         "NNet.Replay.Tracker.SUnitDoneEvent",
         "NNet.Replay.Tracker.SUnitInitEvent",
         "NNet.Replay.Tracker.SUnitPositionsEvent",
         "NNet.Replay.Tracker.SUnitTypeChangeEvent",
         "NNet.Replay.Tracker.SUpgradeEvent"})

  def testGameEvents(self):
    events = list(self._replay.game_events())
    event_types = set(s["_event"] for s in events)

    self.assertEqual(
        event_types,
        {"NNet.Game.SCameraUpdateEvent",
         "NNet.Game.SCmdEvent",
         "NNet.Game.SCmdUpdateTargetPointEvent",
         "NNet.Game.SCmdUpdateTargetUnitEvent",
         "NNet.Game.SCommandManagerStateEvent",
         "NNet.Game.SPeerSetSyncLoadingTimeEvent",
         "NNet.Game.SPeerSetSyncPlayingTimeEvent",
         "NNet.Game.SSelectionDeltaEvent",
         "NNet.Game.SUserFinishedLoadingSyncEvent",
         "NNet.Game.SUserOptionsEvent"})

  def testMessageEvents(self):
    events = list(self._replay.message_events())
    event_types = set(s["_event"] for s in events)

    self.assertEqual(
        event_types,
        {"NNet.Game.SLoadingProgressMessage"})

  def testAttributesEvents(self):
    events = list(self._replay.attributes_events())
    self.assertEmpty(events)


if __name__ == "__main__":
  absltest.main()
