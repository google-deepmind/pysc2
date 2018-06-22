# Copyright 2018 Google Inc. All Rights Reserved.
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
"""portpicker for multiple ports."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import time
import portpicker


def pick_unused_ports(num_ports, retry_interval_secs=3, retry_attempts=5):
  """Reserves and returns a list of `num_ports` unused ports."""
  ports = set()
  for _ in range(retry_attempts):
    ports.update(
        portpicker.pick_unused_port() for _ in range(num_ports - len(ports)))
    ports.discard(None)  # portpicker returns None on error.
    if len(ports) == num_ports:
      return list(ports)
    # Duplicate ports can be returned, especially when insufficient ports are
    # free. Wait for more ports to be freed and retry.
    time.sleep(retry_interval_secs)

  # Could not obtain enough ports. Release what we do have.
  return_ports(ports)

  raise RuntimeError("Unable to obtain %d unused ports." % num_ports)


def pick_contiguous_unused_ports(
    num_ports,
    retry_interval_secs=3,
    retry_attempts=5):
  """Reserves and returns a list of `num_ports` contiguous unused ports."""
  for _ in range(retry_attempts):
    start_port = portpicker.pick_unused_port()
    if start_port is not None:
      ports = [start_port + p for p in range(num_ports)]
      if all(portpicker.is_port_free(p) for p in ports):
        return ports
      else:
        return_ports(ports)

    time.sleep(retry_interval_secs)

  raise RuntimeError("Unable to obtain %d contiguous unused ports." % num_ports)


def return_ports(ports):
  """Returns previously reserved ports so that may be reused."""
  for port in ports:
    portpicker.return_port(port)
