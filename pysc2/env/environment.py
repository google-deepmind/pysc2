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
"""Python RL Environment API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import abc
import collections

import enum
import six


class TimeStep(collections.namedtuple(
    'TimeStep', ['step_type', 'reward', 'discount', 'observation'])):
  """Returned with every call to `step` and `reset` on an environment.

  A `TimeStep` contains the data emitted by an environment at each step of
  interaction. A `TimeStep` holds a `step_type`, an `observation`, and an
  associated `reward` and `discount`.

  The first `TimeStep` in a sequence will have `StepType.FIRST`. The final
  `TimeStep` will have `StepType.LAST`. All other `TimeStep`s in a sequence will
  have `StepType.MID.

  Attributes:
    step_type: A `StepType` enum value.
    reward: A scalar, or 0 if `step_type` is `StepType.FIRST`, i.e. at the
      start of a sequence.
    discount: A discount value in the range `[0, 1]`, or 0 if `step_type`
      is `StepType.FIRST`, i.e. at the start of a sequence.
    observation: A NumPy array, or a dict, list or tuple of arrays.
  """
  __slots__ = ()

  def first(self):
    return self.step_type is StepType.FIRST

  def mid(self):
    return self.step_type is StepType.MID

  def last(self):
    return self.step_type is StepType.LAST


class StepType(enum.IntEnum):
  """Defines the status of a `TimeStep` within a sequence."""
  # Denotes the first `TimeStep` in a sequence.
  FIRST = 0
  # Denotes any `TimeStep` in a sequence that is not FIRST or LAST.
  MID = 1
  # Denotes the last `TimeStep` in a sequence.
  LAST = 2


@six.add_metaclass(abc.ABCMeta)
class Base(object):  # pytype: disable=ignored-abstractmethod
  """Abstract base class for Python RL environments."""

  @abc.abstractmethod
  def reset(self):
    """Starts a new sequence and returns the first `TimeStep` of this sequence.

    Returns:
      A `TimeStep` namedtuple containing:
        step_type: A `StepType` of `FIRST`.
        reward: Zero.
        discount: Zero.
        observation: A NumPy array, or a dict, list or tuple of arrays
          corresponding to `observation_spec()`.
    """

  @abc.abstractmethod
  def step(self, action):
    """Updates the environment according to the action and returns a `TimeStep`.

    If the environment returned a `TimeStep` with `StepType.LAST` at the
    previous step, this call to `step` will start a new sequence and `action`
    will be ignored.

    This method will also start a new sequence if called after the environment
    has been constructed and `restart` has not been called. Again, in this case
    `action` will be ignored.

    Args:
      action: A NumPy array, or a dict, list or tuple of arrays corresponding to
        `action_spec()`.

    Returns:
      A `TimeStep` namedtuple containing:
        step_type: A `StepType` value.
        reward: Reward at this timestep.
        discount: A discount in the range [0, 1].
        observation: A NumPy array, or a dict, list or tuple of arrays
          corresponding to `observation_spec()`.
    """

  @abc.abstractmethod
  def observation_spec(self):
    """Defines the observations provided by the environment.

    Returns:
      A tuple of specs (one per agent), where each spec is a dict of shape
        tuples.
    """

  @abc.abstractmethod
  def action_spec(self):
    """Defines the actions that should be provided to `step`.

    Returns:
      A tuple of specs (one per agent), where each spec is something that
        defines the shape of the actions.
    """

  def close(self):
    """Frees any resources used by the environment.

    Implement this method for an environment backed by an external process.

    This method be used directly

    ```python
    env = Env(...)
    # Use env.
    env.close()
    ```

    or via a context manager

    ```python
    with Env(...) as env:
      # Use env.
    ```
    """
    pass

  def __enter__(self):
    """Allows the environment to be used in a with-statement context."""
    return self

  def __exit__(self, unused_exception_type, unused_exc_value, unused_traceback):
    """Allows the environment to be used in a with-statement context."""
    self.close()

  def __del__(self):
    self.close()

