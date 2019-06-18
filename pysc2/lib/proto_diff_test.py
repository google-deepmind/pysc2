#!/usr/bin/python
# Copyright 2019 Google Inc. All Rights Reserved.
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
"""Tests for proto_diff.py."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl.testing import absltest
from pysc2.lib import proto_diff

from s2clientprotocol import sc2api_pb2 as sc_pb
from s2clientprotocol import score_pb2


class ProtoPathTest(absltest.TestCase):

  def testCreationFromTuple(self):
    self.assertEqual(
        str(proto_diff.ProtoPath(("observation", "actions"))),
        "observation.actions")

  def testCreationFromList(self):
    self.assertEqual(
        str(proto_diff.ProtoPath(["observation", "actions"])),
        "observation.actions")

  def testCreationFromGenerator(self):
    self.assertEqual(
        str(proto_diff.ProtoPath(a for a in "abc")),
        "a.b.c")

  def testStringRepr(self):
    self.assertEqual(
        str(proto_diff.ProtoPath(("observation", "actions", 1, "target"))),
        "observation.actions[1].target")

  def testOrdering(self):
    self.assertLess(
        proto_diff.ProtoPath(("observation", "actions", 1, "game_loop")),
        proto_diff.ProtoPath(("observation", "actions", 1, "target")))

    self.assertLess(
        proto_diff.ProtoPath(("observation", "actions", 1)),
        proto_diff.ProtoPath(("observation", "actions", 1, "target")))

    self.assertGreater(
        proto_diff.ProtoPath(("observation", "actions", 1)),
        proto_diff.ProtoPath(("observation",)))

  def testEquals(self):
    a = proto_diff.ProtoPath(("observation", "actions", 1))
    b = proto_diff.ProtoPath(("observation", "actions", 1))
    self.assertEqual(a, b)
    self.assertEqual(hash(a), hash(b))

  def testNotEqual(self):
    a = proto_diff.ProtoPath(("observation", "actions", 1))
    b = proto_diff.ProtoPath(("observation", "actions", 2))
    self.assertNotEqual(a, b)
    self.assertNotEqual(hash(a), hash(b))

  def testIndexing(self):
    path = proto_diff.ProtoPath(("observation", "actions", 1))
    self.assertEqual(path[0], "observation")
    self.assertEqual(path[1], "actions")
    self.assertEqual(path[-2], "actions")
    self.assertEqual(path[-1], 1)

  def testGetField(self):
    proto = sc_pb.ResponseObservation(
        observation=sc_pb.Observation(game_loop=1, alerts=[sc_pb.AlertError]))

    game_loop = proto_diff.ProtoPath(("observation", "game_loop"))
    alert = proto_diff.ProtoPath(("observation", "alerts", 0))
    self.assertEqual(game_loop.get_field(proto), 1)
    self.assertEqual(alert.get_field(proto), sc_pb.AlertError)
    self.assertEqual(
        proto_diff.ProtoPath(game_loop.path[:-1]).get_field(proto),
        sc_pb.Observation(game_loop=1, alerts=[sc_pb.AlertError]))

  def testWithAnonymousArrayIndices(self):
    a = proto_diff.ProtoPath(("observation", "actions"))
    b = proto_diff.ProtoPath(("observation", "actions", 1))
    c = proto_diff.ProtoPath(("observation", "actions", 2))
    self.assertEqual(str(a), "observation.actions")
    self.assertEqual(
        str(b.with_anonymous_array_indices()), "observation.actions[*]")
    self.assertEqual(
        b.with_anonymous_array_indices(),
        c.with_anonymous_array_indices())


def _alert_formatter(path, proto_a, proto_b):
  field_a = path.get_field(proto_a)
  if path[-2] == "alerts":
    field_b = path.get_field(proto_b)
    return "{} -> {}".format(
        sc_pb.Alert.Name(field_a), sc_pb.Alert.Name(field_b))


class ProtoDiffTest(absltest.TestCase):

  def testNoDiffs(self):
    a = sc_pb.ResponseObservation()
    b = sc_pb.ResponseObservation()
    diff = proto_diff.compute_diff(a, b)
    self.assertIsNone(diff)

  def testAddedField(self):
    a = sc_pb.ResponseObservation()
    b = sc_pb.ResponseObservation(
        observation=sc_pb.Observation(game_loop=1))
    diff = proto_diff.compute_diff(a, b)
    self.assertIsNotNone(diff)
    self.assertLen(diff.added, 1, diff)
    self.assertEqual(str(diff.added[0]), "observation")
    self.assertEqual(diff.added, diff.all_diffs())
    self.assertEqual(diff.report(), "Added observation.")

  def testAddedFields(self):
    a = sc_pb.ResponseObservation(
        observation=sc_pb.Observation(
            alerts=[sc_pb.AlertError]))
    b = sc_pb.ResponseObservation(
        observation=sc_pb.Observation(
            alerts=[sc_pb.AlertError, sc_pb.MergeComplete]),
        player_result=[sc_pb.PlayerResult()])
    diff = proto_diff.compute_diff(a, b)
    self.assertIsNotNone(diff)
    self.assertLen(diff.added, 2, diff)
    self.assertEqual(str(diff.added[0]), "observation.alerts[1]")
    self.assertEqual(str(diff.added[1]), "player_result")
    self.assertEqual(diff.added, diff.all_diffs())
    self.assertEqual(
        diff.report(),
        "Added observation.alerts[1].\n"
        "Added player_result.")

  def testRemovedField(self):
    a = sc_pb.ResponseObservation(observation=sc_pb.Observation(game_loop=1))
    b = sc_pb.ResponseObservation(observation=sc_pb.Observation())
    diff = proto_diff.compute_diff(a, b)
    self.assertIsNotNone(diff)
    self.assertLen(diff.removed, 1, diff)
    self.assertEqual(str(diff.removed[0]), "observation.game_loop")
    self.assertEqual(diff.removed, diff.all_diffs())
    self.assertEqual(
        diff.report(),
        "Removed observation.game_loop.")

  def testRemovedFields(self):
    a = sc_pb.ResponseObservation(observation=sc_pb.Observation(
        game_loop=1,
        score=score_pb2.Score(),
        alerts=[sc_pb.AlertError, sc_pb.MergeComplete]))
    b = sc_pb.ResponseObservation(observation=sc_pb.Observation(
        alerts=[sc_pb.AlertError]))
    diff = proto_diff.compute_diff(a, b)
    self.assertIsNotNone(diff)
    self.assertLen(diff.removed, 3, diff)
    self.assertEqual(str(diff.removed[0]), "observation.alerts[1]")
    self.assertEqual(str(diff.removed[1]), "observation.game_loop")
    self.assertEqual(str(diff.removed[2]), "observation.score")
    self.assertEqual(diff.removed, diff.all_diffs())
    self.assertEqual(
        diff.report(),
        "Removed observation.alerts[1].\n"
        "Removed observation.game_loop.\n"
        "Removed observation.score.")

  def testChangedField(self):
    a = sc_pb.ResponseObservation(observation=sc_pb.Observation(game_loop=1))
    b = sc_pb.ResponseObservation(observation=sc_pb.Observation(game_loop=2))
    diff = proto_diff.compute_diff(a, b)
    self.assertIsNotNone(diff)
    self.assertLen(diff.changed, 1, diff)
    self.assertEqual(str(diff.changed[0]), "observation.game_loop")
    self.assertEqual(diff.changed, diff.all_diffs())
    self.assertEqual(diff.report(), "Changed observation.game_loop: 1 -> 2.")

  def testChangedFields(self):
    a = sc_pb.ResponseObservation(observation=sc_pb.Observation(
        game_loop=1, alerts=[sc_pb.AlertError, sc_pb.LarvaHatched]))
    b = sc_pb.ResponseObservation(observation=sc_pb.Observation(
        game_loop=2, alerts=[sc_pb.AlertError, sc_pb.MergeComplete]))
    diff = proto_diff.compute_diff(a, b)
    self.assertIsNotNone(diff)
    self.assertLen(diff.changed, 2, diff)
    self.assertEqual(str(diff.changed[0]), "observation.alerts[1]")
    self.assertEqual(str(diff.changed[1]), "observation.game_loop")
    self.assertEqual(diff.changed, diff.all_diffs())
    self.assertEqual(
        diff.report(),
        "Changed observation.alerts[1]: 7 -> 8.\n"
        "Changed observation.game_loop: 1 -> 2.")

    self.assertEqual(
        diff.report([_alert_formatter]),
        "Changed observation.alerts[1]: LarvaHatched -> MergeComplete.\n"
        "Changed observation.game_loop: 1 -> 2.")

  def testTruncation(self):
    a = sc_pb.ResponseObservation(observation=sc_pb.Observation(
        game_loop=1, alerts=[sc_pb.AlertError, sc_pb.LarvaHatched]))
    b = sc_pb.ResponseObservation(observation=sc_pb.Observation(
        game_loop=2, alerts=[sc_pb.AlertError, sc_pb.MergeComplete]))
    diff = proto_diff.compute_diff(a, b)
    self.assertIsNotNone(diff)
    self.assertEqual(
        diff.report([_alert_formatter], truncate_to=9),
        "Changed observation.alerts[1]: LarvaH....\n"
        "Changed observation.game_loop: 1 -> 2.")
    self.assertEqual(
        diff.report([_alert_formatter], truncate_to=-1),
        "Changed observation.alerts[1]: ....\n"
        "Changed observation.game_loop: ... -> ....")


if __name__ == "__main__":
  absltest.main()
