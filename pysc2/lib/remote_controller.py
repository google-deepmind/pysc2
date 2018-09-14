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
"""Controllers take actions and generates observations in proto format."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import functools
from absl import logging
import socket
import sys
import time

from absl import flags
from pysc2.lib import protocol
from pysc2.lib import static_data
from pysc2.lib import stopwatch
import websocket

from s2clientprotocol import debug_pb2 as sc_debug
from s2clientprotocol import sc2api_pb2 as sc_pb

flags.DEFINE_bool("sc2_log_actions", False,
                  ("Print all the actions sent to SC2. If you want observations"
                   " as well, consider using `sc2_verbose_protocol`."))
FLAGS = flags.FLAGS

sw = stopwatch.sw

Status = protocol.Status  # pylint: disable=invalid-name


class ConnectError(Exception):
  pass


class RequestError(Exception):

  def __init__(self, description, res):
    super(RequestError, self).__init__(description)
    self.res = res


def check_error(res, error_enum):
  """Raise if the result has an error, otherwise return the result."""
  if res.HasField("error"):
    enum_name = error_enum.DESCRIPTOR.full_name
    error_name = error_enum.Name(res.error)
    details = getattr(res, "error_details", "<none>")
    raise RequestError("%s.%s: '%s'" % (enum_name, error_name, details), res)
  return res


def decorate_check_error(error_enum):
  """Decorator to call `check_error` on the return value."""
  def decorator(func):
    @functools.wraps(func)
    def _check_error(*args, **kwargs):
      return check_error(func(*args, **kwargs), error_enum)
    return _check_error
  return decorator


def skip_status(*skipped):
  """Decorator to skip this call if we're in one of the skipped states."""
  def decorator(func):
    @functools.wraps(func)
    def _skip_status(self, *args, **kwargs):
      if self.status not in skipped:
        return func(self, *args, **kwargs)
    return _skip_status
  return decorator


def valid_status(*valid):
  """Decorator to assert that we're in a valid state."""
  def decorator(func):
    @functools.wraps(func)
    def _valid_status(self, *args, **kwargs):
      if self.status not in valid:
        raise protocol.ProtocolError(
            "`%s` called while in state: %s, valid: (%s)" % (
                func.__name__, self.status, ",".join(map(str, valid))))
      return func(self, *args, **kwargs)
    return _valid_status
  return decorator


def catch_game_end(func):
  """Decorator to handle 'Game has already ended' exceptions."""
  @functools.wraps(func)
  def _catch_game_end(self, *args, **kwargs):
    """Decorator to handle 'Game has already ended' exceptions."""
    prev_status = self.status
    try:
      return func(self, *args, **kwargs)
    except protocol.ProtocolError as protocol_error:
      if prev_status == Status.in_game and (
          "Game has already ended" in str(protocol_error)):
        # It's currently possible for us to receive this error even though
        # our previous status was in_game. This shouldn't happen according
        # to the protocol. It does happen sometimes when we don't observe on
        # every step (possibly also requiring us to be playing against a
        # built-in bot). To work around the issue, we catch the exception
        # and so let the client code continue.
        logging.warning(
            "Received a 'Game has already ended' error from SC2 whilst status "
            "in_game. Suppressing the exception, returning None.")

        return None
      else:
        raise

  return _catch_game_end


class RemoteController(object):
  """Implements a python interface to interact with the SC2 binary.

  All of these are implemented as blocking calls, so wait for the response
  before returning.

  Many of these functions take a Request* object and respond with the
  corresponding Response* object as returned from SC2. The simpler functions
  take a value and construct the Request itself, or return something more useful
  than a Response* object.
  """

  def __init__(self, host, port, proc=None, timeout_seconds=None):
    timeout_seconds = timeout_seconds or 120
    sock = self._connect(host, port, proc, timeout_seconds)
    self._client = protocol.StarcraftProtocol(sock)
    self.ping()

  @sw.decorate
  def _connect(self, host, port, proc, timeout_seconds):
    """Connect to the websocket, retrying as needed. Returns the socket."""
    if ":" in host and not host.startswith("["):  # Support ipv6 addresses.
      host = "[%s]" % host
    url = "ws://%s:%s/sc2api" % (host, port)

    was_running = False
    for i in range(timeout_seconds):
      is_running = proc and proc.running
      was_running = was_running or is_running
      if (i >= timeout_seconds // 4 or was_running) and not is_running:
        logging.warning(
            "SC2 isn't running, so bailing early on the websocket connection.")
        break
      logging.info("Connecting to: %s, attempt: %s, running: %s", url, i,
                   is_running)
      try:
        return websocket.create_connection(url, timeout=timeout_seconds)
      except socket.error:
        pass  # SC2 hasn't started listening yet.
      except websocket.WebSocketBadStatusException as err:
        if err.status_code == 404:
          pass  # SC2 is listening, but hasn't set up the /sc2api endpoint yet.
        else:
          raise
      time.sleep(1)
    raise ConnectError("Failed to connect to the SC2 websocket. Is it up?")

  def close(self):
    self._client.close()

  @valid_status(Status.launched, Status.ended, Status.in_game, Status.in_replay)
  @decorate_check_error(sc_pb.ResponseCreateGame.Error)
  @sw.decorate
  def create_game(self, req_create_game):
    """Create a new game. This can only be done by the host."""
    return self._client.send(create_game=req_create_game)

  @valid_status(Status.launched, Status.init_game)
  @decorate_check_error(sc_pb.ResponseSaveMap.Error)
  @sw.decorate
  def save_map(self, map_path, map_data):
    """Save a map into temp dir so create game can access it in multiplayer."""
    return self._client.send(save_map=sc_pb.RequestSaveMap(
        map_path=map_path, map_data=map_data))

  @valid_status(Status.launched, Status.init_game)
  @decorate_check_error(sc_pb.ResponseJoinGame.Error)
  @sw.decorate
  def join_game(self, req_join_game):
    """Join a game, done by all connected clients."""
    return self._client.send(join_game=req_join_game)

  @valid_status(Status.ended, Status.in_game)
  @decorate_check_error(sc_pb.ResponseRestartGame.Error)
  @sw.decorate
  def restart(self):
    """Restart the game. Only done by the host."""
    return self._client.send(restart_game=sc_pb.RequestRestartGame())

  @valid_status(Status.launched, Status.ended, Status.in_game, Status.in_replay)
  @decorate_check_error(sc_pb.ResponseStartReplay.Error)
  @sw.decorate
  def start_replay(self, req_start_replay):
    """Start a replay."""
    return self._client.send(start_replay=req_start_replay)

  @valid_status(Status.in_game, Status.in_replay)
  @sw.decorate
  def game_info(self):
    """Get the basic information about the game."""
    return self._client.send(game_info=sc_pb.RequestGameInfo())

  @valid_status(Status.in_game, Status.in_replay)
  @sw.decorate
  def data_raw(self):
    """Get the raw static data for the current game. Prefer `data` instead."""
    return self._client.send(data=sc_pb.RequestData(
        ability_id=True, unit_type_id=True))

  def data(self):
    """Get the static data for the current game."""
    return static_data.StaticData(self.data_raw())

  @valid_status(Status.in_game, Status.in_replay, Status.ended)
  @sw.decorate
  def observe(self):
    """Get a current observation."""
    return self._client.send(observation=sc_pb.RequestObservation())

  @valid_status(Status.in_game, Status.in_replay)
  @sw.decorate
  def step(self, count=1):
    """Step the engine forward by one (or more) step."""
    return self._client.send(step=sc_pb.RequestStep(count=count))

  @skip_status(Status.in_replay)
  @valid_status(Status.in_game)
  @catch_game_end
  @sw.decorate
  def actions(self, req_action):
    """Send a `sc_pb.RequestAction`, which may include multiple actions."""
    if FLAGS.sc2_log_actions:
      for action in req_action.actions:
        sys.stderr.write(str(action))
        sys.stderr.flush()

    return self._client.send(action=req_action)

  def act(self, action):
    """Send a single action. This is a shortcut for `actions`."""
    if action and action.ListFields():  # Skip no-ops.
      return self.actions(sc_pb.RequestAction(actions=[action]))

  def chat(self, message):
    """Send chat message as a broadcast."""
    if message:
      action_chat = sc_pb.ActionChat(
          channel=sc_pb.ActionChat.Broadcast, message=message)
      action = sc_pb.Action(action_chat=action_chat)
      return self.act(action)

  @valid_status(Status.in_game, Status.ended)
  @sw.decorate
  def leave(self):
    """Disconnect from a multiplayer game."""
    return self._client.send(leave_game=sc_pb.RequestLeaveGame())

  @valid_status(Status.in_game, Status.ended)
  @sw.decorate
  def save_replay(self):
    """Save a replay, returning the data."""
    res = self._client.send(save_replay=sc_pb.RequestSaveReplay())
    return res.data

  @valid_status(Status.in_game)
  @sw.decorate
  def debug(self, debug_commands):
    """Run a debug command."""
    if isinstance(debug_commands, sc_debug.DebugCommand):
      debug_commands = [debug_commands]
    return self._client.send(debug=sc_pb.RequestDebug(debug=debug_commands))

  @skip_status(Status.quit)
  @sw.decorate
  def quit(self):
    """Shut down the SC2 process."""
    try:
      # Don't expect a response.
      self._client.write(sc_pb.Request(quit=sc_pb.RequestQuit()))
    except protocol.ConnectionError:
      pass  # It's likely already (shutting) down, so continue as if it worked.
    finally:
      self.close()

  @sw.decorate
  def ping(self):
    return self._client.send(ping=sc_pb.RequestPing())

  @decorate_check_error(sc_pb.ResponseReplayInfo.Error)
  @sw.decorate
  def replay_info(self, replay_data):
    return self._client.send(replay_info=sc_pb.RequestReplayInfo(
        replay_data=replay_data))

  @property
  def status(self):
    return self._client.status
