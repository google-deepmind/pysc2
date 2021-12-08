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
"""PySC2 environment converter.

This is a thin wrapper around the pybind implementation, supporting dm specs
and numpy arrays in place of dm_env_rpc protos; also supports documentation
more naturally.
"""

from typing import Any, Mapping

from dm_env import specs
from pysc2.env.converter.cc.python import converter
from pysc2.env.converter.proto import converter_pb2

from dm_env_rpc.v1 import dm_env_utils
from dm_env_rpc.v1 import tensor_utils
from s2clientprotocol import sc2api_pb2


class Converter:
  """PySC2 environment converter.

  Converts the PySC2 observation/action interface, supporting more standard
  interaction with an ML agent and providing enriched observations.

  Limited configuration is supported through the `ConverterSettings` proto.
  In particular, clients may choose between 'visual' and 'raw' interfaces.
  The visual interface focuses on spatial features and actions which are close
  to those used by a human when playing the game. The raw interface retains
  some spatial features but focuses on numeric unit data; actions being
  specified to units directly, ignoring e.g. the position of the camera.

  The converter maintains some state throughout an episode. This state relies
  on convert_observation and convert_action being called alternately
  throughout the episde. A new converter should be created for each episode.
  """

  def __init__(self, settings: converter_pb2.ConverterSettings,
               environment_info: converter_pb2.EnvironmentInfo):
    self._converter = converter.MakeConverter(
        settings=settings.SerializeToString(),
        environment_info=environment_info.SerializeToString())

  def observation_spec(self) -> Mapping[str, specs.Array]:
    """Returns the observation spec.

    This is a flat mapping of string label to dm_env array spec and varies
    with the specified converter settings and instantiated environment info.
    """
    return {
        k: dm_env_utils.tensor_spec_to_dm_env_spec(v)
        for k, v in self._converter.ObservationSpec().items()
    }

  def action_spec(self) -> Mapping[str, specs.Array]:
    """Returns the action spec.

    This is a flat mapping of string label to dm_env array spec and varies
    with the specified converter settings and instantiated environment info.
    """
    return {
        k: dm_env_utils.tensor_spec_to_dm_env_spec(v)
        for k, v in self._converter.ActionSpec().items()
    }

  def convert_observation(
      self, observation: converter_pb2.Observation) -> Mapping[str, Any]:
    """Converts a SC2 API observation, enriching it with additional info.

    Args:
      observation: Proto containing the SC2 API observation proto for the
        player, and potentially for his opponent. When operating in supervised
        mode must also contain the action taken by the player in response to
        this observation.

    Returns:
      A flat mapping of string labels to numpy arrays / or scalars, as
      appropriate.
    """
    for k, v in self._converter.ConvertObservation(observation).items():
      try:
        tensor_utils.unpack_tensor(v)
      except Exception as e:
        raise Exception(f'Failed for {k}:{v} - {e}')

    return {
        k: tensor_utils.unpack_tensor(v)
        for k, v in self._converter.ConvertObservation(observation).items()
    }

  def convert_action(self, action: Mapping[str, Any]) -> converter_pb2.Action:
    """Converts an agent action into an SC2 API action proto.

    Note that the returned action also carries the game loop delay requested
    by this player until the next observation.

    Args:
      action: A flat mapping of string labels to numpy arrays / or scalars.

    Returns:
      An SC2 API action request + game loop delay.
    """
    # TODO(b/207106690):
    # This is necessary at the moment because pybind11 returns wrapped
    # protos which are not the same class as the native Python proto.
    # That makes e.g. instanceof checks fail elsewhere in the code.
    # Once we switch to native_proto_casters.h the problem goes away.
    transformed = self._converter.ConvertAction(
        {k: tensor_utils.pack_tensor(v) for k, v in action.items()})
    request_action = sc2api_pb2.RequestAction()
    request_action.ParseFromString(
        transformed.request_action.SerializeToString())
    return converter_pb2.Action(
        request_action=request_action, delay=transformed.delay)
