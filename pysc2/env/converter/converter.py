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

from dm_env_rpc.v1 import dm_env_rpc_pb2
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
    spec = {}
    for k, v in self._converter.ObservationSpec().items():
      value = dm_env_rpc_pb2.TensorSpec()
      value.ParseFromString(v)
      spec[k] = dm_env_utils.tensor_spec_to_dm_env_spec(value)
    return spec

  def action_spec(self) -> Mapping[str, specs.Array]:
    """Returns the action spec.

    This is a flat mapping of string label to dm_env array spec and varies
    with the specified converter settings and instantiated environment info.
    """
    spec = {}
    for k, v in self._converter.ActionSpec().items():
      value = dm_env_rpc_pb2.TensorSpec()
      value.ParseFromString(v)
      spec[k] = dm_env_utils.tensor_spec_to_dm_env_spec(value)
    return spec

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
    serialized_converted_obs = self._converter.ConvertObservation(
        observation.SerializeToString())

    deserialized_converted_obs = {}
    for k, v in serialized_converted_obs.items():
      value = dm_env_rpc_pb2.Tensor()
      value.ParseFromString(v)
      try:
        unpacked_value = tensor_utils.unpack_tensor(value)
        deserialized_converted_obs[k] = unpacked_value
      except Exception as e:
        raise Exception(f'Unpacking failed for {k}:{v} - {e}')

    return deserialized_converted_obs

  def convert_action(self, action: Mapping[str, Any]) -> converter_pb2.Action:
    """Converts an agent action into an SC2 API action proto.

    Note that the returned action also carries the game loop delay requested
    by this player until the next observation.

    Args:
      action: A flat mapping of string labels to numpy arrays / or scalars.

    Returns:
      An SC2 API action request + game loop delay.
    """
    # TODO(b/210113354): Remove protos serialization over pybind11 boundary.
    serialized_action = {
        k: tensor_utils.pack_tensor(v).SerializeToString()
        for k, v in action.items()
    }
    converted_action_serialized = self._converter.ConvertAction(
        serialized_action)
    converted_action = converter_pb2.Action()
    converted_action.ParseFromString(converted_action_serialized)

    request_action = sc2api_pb2.RequestAction()
    request_action.ParseFromString(
        converted_action.request_action.SerializeToString())
    return converter_pb2.Action(
        request_action=request_action, delay=converted_action.delay)
