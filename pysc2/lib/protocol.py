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
"""Protocol library to make communication easy."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import contextlib
from absl import logging
import os
import socket
import sys
import time

from absl import flags
import enum
from pysc2.lib import stopwatch
import websocket

from s2clientprotocol import sc2api_pb2 as sc_pb


flags.DEFINE_integer("sc2_verbose_protocol", 0,
                     ("Print the communication packets with SC2. 0 disables. "
                      "-1 means all. >0 will print that many lines per "
                      "packet. 20 is a good starting value."))
FLAGS = flags.FLAGS


sw = stopwatch.sw

# Create a python version of the Status enum in the proto.
Status = enum.Enum("Status", sc_pb.Status.items())  # pylint: disable=invalid-name


class ConnectionError(Exception):
  """Failed to read/write a message, details in the error string."""
  pass


class ProtocolError(Exception):
  """SC2 responded with an error message likely due to a bad request or bug."""
  pass


@contextlib.contextmanager
def catch_websocket_connection_errors():
  """A context manager that translates websocket errors into ConnectionError."""
  try:
    yield
  except websocket.WebSocketConnectionClosedException:
    raise ConnectionError("Connection already closed. SC2 probably crashed. "
                          "Check the error log.")
  except websocket.WebSocketTimeoutException:
    raise ConnectionError("Websocket timed out.")
  except socket.error as e:
    raise ConnectionError("Socket error: %s" % e)


class StarcraftProtocol(object):
  """Defines the protocol for chatting with starcraft."""

  def __init__(self, sock):
    self._status = Status.launched
    self._sock = sock

  @property
  def status(self):
    return self._status

  def close(self):
    if self._sock:
      self._sock.close()
      self._sock = None
    self._status = Status.quit

  @sw.decorate
  def read(self):
    """Read a Response, do some validation, and return it."""
    if FLAGS.sc2_verbose_protocol:
      self._log(" Reading response ".center(60, "-"))
      start = time.time()
    response = self._read()
    if FLAGS.sc2_verbose_protocol:
      self._log(" %0.1f msec\n" % (1000 * (time.time() - start)))
      self._log_packet(response)
    if not response.HasField("status"):
      raise ProtocolError("Got an incomplete response without a status.")
    prev_status = self._status
    self._status = Status(response.status)  # pytype: disable=not-callable
    if response.error:
      err_str = ("Error in RPC response (likely a bug). "
                 "Prev status: %s, new status: %s, error:\n%s" % (
                     prev_status, self._status, "\n".join(response.error)))
      logging.error(err_str)
      raise ProtocolError(err_str)
    return response

  @sw.decorate
  def write(self, request):
    """Write a Request."""
    if FLAGS.sc2_verbose_protocol:
      self._log(" Writing request ".center(60, "-") + "\n")
      self._log_packet(request)
    self._write(request)

  def send_req(self, request):
    """Write a pre-filled Request and return the Response."""
    self.write(request)
    return self.read()

  def send(self, **kwargs):
    """Create and send a specific request, and return the response.

    For example: send(ping=sc_pb.RequestPing()) => sc_pb.ResponsePing

    Args:
      **kwargs: A single kwarg with the name and value to fill in to Request.

    Returns:
      The Response corresponding to your request.
    """
    assert len(kwargs) == 1, "Must make a single request."
    res = self.send_req(sc_pb.Request(**kwargs))
    return getattr(res, list(kwargs.keys())[0])

  def _log_packet(self, packet):
    max_lines = FLAGS.sc2_verbose_protocol
    if max_lines > 0:
      max_width = int(os.getenv("COLUMNS", 200))  # Get your TTY width.
      lines = str(packet).strip().split("\n")
      self._log("".join(line[:max_width] + "\n" for line in lines[:max_lines]))
      if len(lines) > max_lines:
        self._log(("**** %s lines skipped ****\n" % (len(lines) - max_lines)))
    else:
      self._log("%s\n" % packet)

  def _log(self, s):
    r"""Log a string. It flushes but doesn't append \n, so do that yourself."""
    # TODO(tewalds): Should this be using logging.info instead? How to see them
    # outside of google infrastructure?
    sys.stderr.write(s)
    sys.stderr.flush()

  def _read(self):
    """Actually read the response and parse it, returning a Response."""
    with sw("read_response"):
      with catch_websocket_connection_errors():
        response_str = self._sock.recv()
    if not response_str:
      raise ProtocolError("Got an empty response from SC2.")
    response = sc_pb.Response()
    with sw("parse_response"):
      response.ParseFromString(response_str)
    return response

  def _write(self, request):
    """Actually serialize and write the request."""
    with sw("serialize_request"):
      request_str = request.SerializeToString()
    with sw("write_request"):
      with catch_websocket_connection_errors():
        self._sock.send(request_str)
