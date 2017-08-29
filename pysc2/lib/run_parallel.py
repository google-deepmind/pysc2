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
"""A thread pool for running a set of functions synchronously in parallel.

This is mainly intended for use where the functions have a barrier and none will
return until all have been called.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import functools

from concurrent import futures


class RunParallel(object):
  """Run all funcs in parallel."""

  def __init__(self, timeout=None):
    self._timeout = timeout
    self._executor = None
    self._workers = 0

  def run(self, funcs):
    """Run a set of functions in parallel, returning their results.

    Make sure any function you pass exits with a reasonable timeout. If it
    doesn't return within the timeout or the result is ignored due an exception
    in a separate thread it will continue to stick around until it finishes,
    including blocking process exit.

    Args:
      funcs: An iterable of functions or iterable of args to functools.partial.

    Returns:
      A list of return values with the values matching the order in funcs.

    Raises:
      Propagates the first exception encountered in one of the functions.
    """
    funcs = [f if callable(f) else functools.partial(*f) for f in funcs]
    if len(funcs) == 1:  # Ignore threads if it's not needed.
      return [funcs[0]()]
    if len(funcs) > self._workers:  # Lazy init and grow as needed.
      self.shutdown()
      self._workers = len(funcs)
      self._executor = futures.ThreadPoolExecutor(self._workers)
    futs = [self._executor.submit(f) for f in funcs]
    done, not_done = futures.wait(futs, self._timeout, futures.FIRST_EXCEPTION)
    # Make sure to propagate any exceptions.
    for f in done:
      if not f.cancelled() and f.exception() is not None:
        if not_done:
          # If there are some calls that haven't finished, cancel and recreate
          # the thread pool. Otherwise we may have a thread running forever
          # blocking parallel calls.
          for nd in not_done:
            nd.cancel()
          self.shutdown(False)  # Don't wait, they may be deadlocked.
        raise f.exception()
    # Either done or timed out, so don't wait again.
    return [f.result(timeout=0) for f in futs]

  def shutdown(self, wait=True):
    if self._executor:
      self._executor.shutdown(wait)
      self._executor = None
      self._workers = 0

  def __del__(self):
    self.shutdown()
