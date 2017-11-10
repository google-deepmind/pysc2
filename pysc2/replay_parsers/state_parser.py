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
import numpy as np

from pysc2.replay_parsers import base_parser

from s2clientprotocol import sc2api_pb2 as sc_pb
from s2clientprotocol import common_pb2 as sc_common

def calc_armies(screen):
	friendly_army = []
	enemy_army = []
	unit_list = np.unique(screen[6])
	for unit in unit_list:
		friendly_pixels = (screen[5] == 1) & (screen[6] == unit)
		friendly_unit_count = sum(screen[11,friendly_pixels])
	#only append if count > 0
		if friendly_unit_count:
			friendly_army.append([int(unit),friendly_unit_count])
		enemy_pixels = (screen[5] == 4) & (screen[6] == unit)
		enemy_unit_count = sum(screen[11,enemy_pixels])
		if enemy_unit_count:
			enemy_army.append([int(unit), enemy_unit_count])
	return friendly_army, enemy_army

def update_minimap(minimap,screen):
	#Update minimap data with screen details
	#Identify which minimap squares are on screen
	visible = minimap[1] == 1
	#TODO: need to devide screen into visible minimap, for now
	#devide each quantity by number of visible minimap squares
	total_visible = sum(visible.ravel())
	#power
	minimap[4,visible] = (sum(screen[3].ravel())/
						  (len(screen[3].ravel())*total_visible))
	#friendy army
	friendly_units = screen[5] == 1
	#unit density
	minimap[5,visible] = sum(screen[11,friendly_units])/total_visible
	#Most common unit
	if friendly_units.any() == True:
		minimap[6,visible] = np.bincount(screen[6,friendly_units]).argmax()
	else:
		minimap[6,visible] = 0
	#Total HP + Shields
	minimap[7,visible] = ((sum(screen[8,friendly_units]) + 
						  sum(screen[10,friendly_units]))/total_visible)
	#enemy army
	enemy_units = screen[5] == 4
	#unit density
	minimap[8,visible] = sum(screen[11,enemy_units])/total_visible
	#main unit
	if enemy_units.any() == True:
		minimap[9,visible] = np.bincount(screen[6,enemy_units]).argmax()
	else:
		minimap[9,visible] = 0
	#Total HP + shields
	minimap[10,visible] = ((sum(screen[8,enemy_units]) + 
							sum(screen[10,friendly_units]))/total_visible)

	return minimap

class StateParser(base_parser.BaseParser):
	"""Action statistics parser for replays."""
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

	def parse_step(self,obs,feat,info):
		actions = []
		for action in obs.actions:
			try:
				full_act = feat.reverse_action(action)
				func = full_act.function
				args = full_act.arguments
			except ValueError:
				func = -1
				args = []

			actions.append([func,args])

		all_features = feat.transform_obs(obs.observation)
		#remove elevation, viz and selected data from minimap
		minimap_data = all_features['minimap'][2:6,:,:]
		screen = all_features['screen']

		mini_shape = minimap_data.shape
		minimap = np.zeros(shape=(11,mini_shape[1],mini_shape[2]),dtype=np.int)
		minimap[0:4,:,:] = minimap_data
		extended_minimap = update_minimap(minimap,screen).tolist()
		friendly_army, enemy_army = calc_armies(screen)

		if info.player_info[0].player_result.result == 'Victory':
			winner = 1
		else:
			winner = 2
		for player_id in [1, 2]:
			race = sc_common.Race.Name(info.player_info[player_id-1].player_info.race_actual)
			if player_id == 1:
				enemy = 2
			else:
				enemy = 1 
		enemy_race = sc_common.Race.Name(info.player_info[enemy-1].player_info.race_actual)
		
		full_state = [info.map_name, extended_minimap,
					friendly_army,enemy_army,all_features['player'].tolist(),
					all_features['available_actions'].tolist(),actions,winner,
					race,enemy_race]
		return full_state