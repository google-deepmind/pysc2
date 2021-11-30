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
"""SC2 replays -> ResponseObservation proto streams."""

import io
import json
import time

from absl import logging
import mpyq
from pysc2 import run_configs

from s2clientprotocol import sc2api_pb2 as sc_pb


def _get_replay_version(replay_data):
  replay_io = io.BytesIO()
  replay_io.write(replay_data)
  replay_io.seek(0)
  archive = mpyq.MPQArchive(replay_io).extract()
  metadata = json.loads(
      bytes.decode(archive[b"replay.gamemetadata.json"], "utf-8"))
  return run_configs.lib.Version(
      game_version=".".join(metadata["GameVersion"].split(".")[:-1]),
      build_version=int(metadata["BaseBuild"][4:]),
      data_version=metadata.get("DataVersion"),  # Only in replays version 4.1+.
      binary=None)


class ReplayError(Exception):
  pass


class ReplayObservationStream(object):
  """Wrapper class for iterating over replay observation data.

  Yields the observations for a replay from player_id's perspective. The class
  can throw connection errors from the controller. These should be caught
  at the top level, since they are unrecoverable (the controller is unusable).

  Determines the replay version from the protocol information in the replay
  file. Uses a cache of processes, one for each binary version required
  to process corresponding replays.

  How to use the class:

  with ReplayObservationStream() as replay_stream:
    replay_stream.start_replay(replay_data, player_id)

    # Get game data if needed.
    info = replay_stream.game_info()

    for observation in replay_stream.observations():
      # Do something with each observation.
  """

  def __init__(self,
               interface_options: sc_pb.InterfaceOptions,
               step_mul: int = 1,
               disable_fog: bool = False,
               game_steps_per_episode: int = 0,
               add_opponent_observations: bool = False):
    """Constructs the replay stream object.

    Args:
      interface_options: Interface format to use.
      step_mul: Number of skipped observations in between environment steps.
      disable_fog: Bool, True to disable fog of war.
      game_steps_per_episode: Int, truncate after this many steps (0 for inf.).
      add_opponent_observations: Bool, True to return the opponent's
          observations in addition to the observing player. Note that this will
          start two SC2 processes simultaneously if set to True. By default is
          False and returns observations from one player's perspective.
    """
    self._step_mul = step_mul
    self._disable_fog = disable_fog
    self._game_steps_per_episode = game_steps_per_episode
    self._add_opponent_observations = add_opponent_observations

    self._packet_count = 0
    self._info = None
    self._player_id = None

    if not interface_options:
      raise ValueError("Please specify interface_options")

    self._interface = interface_options
    self._want_rgb = self._interface.HasField("render")

    self._run_config = None
    self._sc2_procs = []
    self._controllers = []

  def _get_controllers(self, version):
    """Get controllers."""
    if not self._run_config or self._run_config.version != version:
      # Close current process and create a new one.
      self._close()
      self._run_config = run_configs.get(version=version)
      self._sc2_procs = [self._run_config.start(want_rgb=self._want_rgb)]
      if self._add_opponent_observations:
        self._sc2_procs.append(self._run_config.start(want_rgb=self._want_rgb))

      self._controllers = [
          proc.controller for proc in self._sc2_procs
      ]

    return self._controllers

  def _close(self):
    self._run_config = None
    for controller in self._controllers:
      if controller:
        controller.quit()
    self._controllers = []
    for proc in self._sc2_procs:
      if proc:
        proc.close()
    self._sc2_procs = []

  def start_replay_from_data(self, replay_data, player_id):
    """Starts the stream of replay observations from an in-memory replay."""
    self._player_id = player_id

    try:
      version = _get_replay_version(replay_data)
    except (ValueError, AttributeError) as err:
      logging.exception("Error getting replay version from data: %s", err)
      raise ReplayError(err)

    if self._add_opponent_observations:
      player_ids = [player_id, (player_id % 2) + 1]
    else:
      player_ids = [player_id]
    start_requests = []
    for p_id in player_ids:
      start_requests.append(
          sc_pb.RequestStartReplay(
              replay_data=replay_data,
              options=self._interface,
              disable_fog=self._disable_fog,
              observed_player_id=p_id))

    logging.info("Starting replay...")

    self._controllers = self._get_controllers(version)
    self._info = info = self._controllers[0].replay_info(replay_data)
    logging.info(" Replay info ".center(60, "-"))
    logging.info(info)
    logging.info("-" * 60)

    if (info.local_map_path and
        info.local_map_path.lower().endswith(".sc2map")):
      logging.info("Map path: %s", info.local_map_path)
      for start_replay in start_requests:
        start_replay.map_data = self._run_config.map_data(info.local_map_path)

    for controller, start_replay in zip(self._controllers, start_requests):
      controller.start_replay(start_replay)
    logging.info("Getting started...")

  def replay_info(self):
    return self._info

  def game_info(self):
    return self._controllers[0].game_info()

  def static_data(self):
    return self._controllers[0].data()

  def observations(self, step_sequence=None):
    """Yields a ResponseObservation proto for each environment step.

    If using the opponent's observations, this will yield a list of
    observations, one for each player.

    Args:
      step_sequence: A list of integers, the step sizes to apply to the stream.
    """
    self._packet_count = 0
    period_start = time.time()
    period = 1000  # log packet rate every 1000 packets
    logging.info("Begin iterating over frames...")

    while True:
      obs = [controller.observe() for controller in self._controllers]
      if self._packet_count == 0:
        logging.info("The first packet has been read")
      self._packet_count += 1
      if len(obs) == 1:
        yield obs[0]
      else:
        yield obs

      if (obs[0].player_result or
          (step_sequence and self._packet_count > len(step_sequence))):
        # End of game.
        break

      if self._game_steps_per_episode > 0:
        if obs[0].observation.game_loop >= self._game_steps_per_episode - 1:
          break

      for controller in self._controllers:
        if step_sequence and self._packet_count <= len(step_sequence):
          step_mul = step_sequence[self._packet_count - 1]
        else:
          step_mul = self._step_mul

        controller.step(step_mul)

      if self._packet_count % period == 0:
        time_taken = time.time() - period_start
        period_start = time.time()
        logging.info(
            "Frame: %d, packets per sec: %.1f",
            obs[0].observation.game_loop, period / time_taken)

  def close(self):
    """Close the replay process connection."""
    logging.info("Quitting...")
    self._close()

  def __enter__(self):
    return self

  def __exit__(self, exception_type, exception_value, traceback):
    if exception_value:
      logging.error("[%s]: %s", exception_type, exception_value)

    self.close()
