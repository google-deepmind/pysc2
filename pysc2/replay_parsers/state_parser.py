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
"""Action statistics parser for replays."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import six

from pysc2.replay_parsers import base_parser

class ActionParser(base_parser.BaseParser):
	"""Action statistics parser for replays."""

	def __init__(self):
		super(ActionParser, self).__init__()
		self.camera_move = 0
		self.select_pt = 0
		self.select_rect = 0
		self.control_group = 0
		self.unit_ids = collections.defaultdict(int)
		self.valid_abilities = collections.defaultdict(int)
		self.made_abilities = collections.defaultdict(int)
		self.valid_actions = collections.defaultdict(int)
		self.made_actions = collections.defaultdict(int)

	def merge(self, other):
		"""Merge another ReplayStats into this one."""
		def merge_dict(a, b):
			for k, v in six.iteritems(b):
				a[k] += v
		super(ActionParser,self).merge(other)      
		self.camera_move += other.camera_move
		self.select_pt += other.select_pt
		self.select_rect += other.select_rect
		self.control_group += other.control_group
		merge_dict(self.unit_ids, other.unit_ids)
		merge_dict(self.valid_abilities, other.valid_abilities)
		merge_dict(self.made_abilities, other.made_abilities)
		merge_dict(self.valid_actions, other.valid_actions)
		merge_dict(self.made_actions, other.made_actions)

	def valid_replay(self,info, ping):
		return True
		"""Make sure the replay isn't corrupt, and is worth looking at."""
		if (info.HasField("error") or
		info.base_build != ping.base_build or  # different game version
		info.game_duration_loops < 1000 or
		len(info.player_info) != 2):
		# Probably corrupt, or just not interesting.
			return False
		for p in info.player_info:
			if p.player_apm < 10 or p.player_mmr < 1000:
		# Low APM = player just standing around.
		# Low MMR = corrupt replay or player who is weak.
				return False
		return True

	def __str__(self):
		len_sorted_dict = lambda s: (len(s), self.sorted_dict_str(s))
		len_sorted_list = lambda s: (len(s), sorted(s))
		return "\n\n".join((
		"Replays: %s, Steps total: %s" % (self.replays, self.steps),
		"Camera move: %s, Select pt: %s, Select rect: %s, Control group: %s" % (
		self.camera_move, self.select_pt, self.select_rect,
		self.control_group),
		"Maps: %s\n%s" % len_sorted_dict(self.maps),
		"Races: %s\n%s" % len_sorted_dict(self.races),
		"Unit ids: %s\n%s" % len_sorted_dict(self.unit_ids),
		"Valid abilities: %s\n%s" % len_sorted_dict(self.valid_abilities),
		"Made abilities: %s\n%s" % len_sorted_dict(self.made_abilities),
		"Valid actions: %s\n%s" % len_sorted_dict(self.valid_actions),
		"Made actions: %s\n%s" % len_sorted_dict(self.made_actions),
		"Crashing replays: %s\n%s" % len_sorted_list(self.crashing_replays),
		"Invalid replays: %s\n%s" % len_sorted_list(self.invalid_replays),
		))

	def parse_step(self,obs,feat):
		for action in obs.actions:
			act_fl = action.action_feature_layer
			if act_fl.HasField("unit_command"):
				self.made_abilities[
					act_fl.unit_command.ability_id] += 1
			if act_fl.HasField("camera_move"):
				self.camera_move += 1
			if act_fl.HasField("unit_selection_point"):
				self.select_pt += 1
			if act_fl.HasField("unit_selection_rect"):
				self.select_rect += 1
			if action.action_ui.HasField("control_group"):
				self.control_group += 1

			try:
				func = feat.reverse_action(action).function
			except ValueError:
				func = -1
				self.made_actions[func] += 1

		for valid in obs.observation.abilities:
			self.valid_abilities[valid.ability_id] += 1

		for u in obs.observation.raw_data.units:
			self.unit_ids[u.unit_type] += 1

		for ability_id in feat.available_actions(obs.observation):
			self.valid_actions[ability_id] += 1