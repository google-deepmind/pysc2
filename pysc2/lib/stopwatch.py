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
"""A stopwatch to check how much time is used by bits of code."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from collections import defaultdict
import functools
import math
import os
import sys
import threading
import time

from future.builtins import range  # pylint: disable=redefined-builtin
import six


class Stat(object):
  """A set of statistics about a single value series."""
  __slots__ = ("num", "min", "max", "sum", "sum_sq")

  def __init__(self):
    self.reset()

  def reset(self):
    self.num = 0
    self.min = 1000000000
    self.max = 0
    self.sum = 0
    self.sum_sq = 0

  def add(self, val):
    self.num += 1
    if self.min > val:
      self.min = val
    if self.max < val:
      self.max = val
    self.sum += val
    self.sum_sq += val**2

  @property
  def avg(self):
    return 0 if self.num == 0 else self.sum / self.num

  @property
  def dev(self):
    """Standard deviation."""
    if self.num == 0:
      return 0
    return math.sqrt(max(0, self.sum_sq / self.num - (self.sum / self.num)**2))

  def merge(self, other):
    self.num += other.num
    self.min = min(self.min, other.min)
    self.max = max(self.max, other.max)
    self.sum += other.sum
    self.sum_sq += other.sum_sq

  @staticmethod
  def build(summation, average, standard_deviation, minimum, maximum, number):
    stat = Stat()
    if number > 0:
      stat.num = number
      stat.min = minimum
      stat.max = maximum
      stat.sum = summation
      stat.sum_sq = number * (standard_deviation**2 + average**2)
    return stat

  @staticmethod
  def parse(s):
    if s == "num=0":
      return Stat()
    parts = (float(p.split(":")[1]) for p in s.split(", "))
    return Stat.build(*parts)

  def __str__(self):
    if self.num == 0:
      return "num=0"
    return "sum: %.4f, avg: %.4f, dev: %.4f, min: %.4f, max: %.4f, num: %d" % (
        self.sum, self.avg, self.dev, self.min, self.max, self.num)


class StopWatchContext(object):
  """Time an individual call."""
  __slots__ = ("_sw", "_start")

  def __init__(self, stopwatch, name):
    self._sw = stopwatch
    self._sw.push(name)

  def __enter__(self):
    self._start = time.time()

  def __exit__(self, unused_exception_type, unused_exc_value, unused_traceback):
    self._sw.add(self._sw.pop(), time.time() - self._start)


class TracingStopWatchContext(StopWatchContext):
  """Time an individual call, but also output all the enter/exit calls."""

  def __enter__(self):
    super(TracingStopWatchContext, self).__enter__()
    self._log(">>> %s" % self._sw.cur_stack())

  def __exit__(self, *args, **kwargs):
    self._log("<<< %s: %.6f secs" % (self._sw.cur_stack(),
                                     time.time() - self._start))
    super(TracingStopWatchContext, self).__exit__(*args, **kwargs)

  def _log(self, s):
    print(s, file=sys.stderr)


class FakeStopWatchContext(object):
  """A fake stopwatch context for when the stopwatch is too slow or unneeded."""
  __slots__ = ()

  def __enter__(self):
    pass

  def __exit__(self, unused_exception_type, unused_exc_value, unused_traceback):
    pass


fake_context = FakeStopWatchContext()


class StopWatch(object):
  """A context manager that tracks call count and latency, and other stats.

  Usage:
      sw = stopwatch.Stopwatch()
      with sw("foo"):
        foo()
      with sw("bar"):
        bar()
      @sw.decorate
      def func():
        pass
      func()
      print(sw)
  """
  __slots__ = ("_times", "_local", "enabled", "trace")

  def __init__(self, enabled=True, trace=False):
    self._times = defaultdict(Stat)
    self._local = threading.local()
    self.enabled = enabled
    self.trace = trace

  def __call__(self, name):
    if not self.enabled:  # This is the usual fast case.
      return fake_context
    if self.trace:
      return TracingStopWatchContext(self, name)
    else:
      return StopWatchContext(self, name)

  def decorate(self, name_or_func):
    """Decorate a function/method to check its timings.

    To use the function's name:
      @sw.decorate
      def func():
        pass

    To name it explicitly:
      @sw.decorate("name")
      def random_func_name():
        pass

    Args:
      name_or_func: the name or the function to decorate.

    Returns:
      If a name is passed, returns this as a decorator, otherwise returns the
      decorated function.
    """
    if os.environ.get("SC2_NO_STOPWATCH"):
      return name_or_func if callable(name_or_func) else lambda func: func

    def decorator(name, func):
      @functools.wraps(func)
      def _stopwatch(*args, **kwargs):
        with self(name):
          return func(*args, **kwargs)
      return _stopwatch
    if callable(name_or_func):
      return decorator(name_or_func.__name__, name_or_func)
    else:
      return lambda func: decorator(name_or_func, func)

  def push(self, name):
    try:
      self._local.stack.append(name)
    except AttributeError:
      # Using an exception is faster than using hasattr.
      self._local.stack = [name]

  def pop(self):
    stack = self._local.stack
    ret = ".".join(stack)
    stack.pop()
    return ret

  def cur_stack(self):
    return ".".join(self._local.stack)

  def clear(self):
    self._times.clear()

  def add(self, name, duration):
    self._times[name].add(duration)

  def __getitem__(self, name):
    return self._times[name]

  @property
  def times(self):
    return self._times

  def merge(self, other):
    for k, v in six.iteritems(other.times):
      self._times[k].merge(v)

  @staticmethod
  def parse(s):
    """Parse the output below to create a new StopWatch."""
    stopwatch = StopWatch()
    for line in s.splitlines():
      if line.strip():
        parts = line.split(None)
        name = parts[0]
        if name != "%":  # ie not the header line
          rest = (float(v) for v in parts[2:])
          stopwatch.times[parts[0]].merge(Stat.build(*rest))
    return stopwatch

  def str(self, threshold=0.1):
    """Return a string representation of the timings."""
    if not self._times:
      return ""
    total = sum(s.sum for k, s in six.iteritems(self._times) if "." not in k)
    table = [["", "% total", "sum", "avg", "dev", "min", "max", "num"]]
    for k, v in sorted(self._times.items()):
      percent = 100 * v.sum / (total or 1)
      if percent > threshold:  # ignore anything below the threshold
        table.append([
            k,
            "%.2f%%" % percent,
            "%.4f" % v.sum,
            "%.4f" % v.avg,
            "%.4f" % v.dev,
            "%.4f" % v.min,
            "%.4f" % v.max,
            "%d" % v.num,
        ])
    col_widths = [max(len(row[i]) for row in table)
                  for i in range(len(table[0]))]

    out = ""
    for row in table:
      out += "  " + row[0].ljust(col_widths[0]) + "  "
      out += "  ".join(
          val.rjust(width) for val, width in zip(row[1:], col_widths[1:]))
      out += "\n"
    return out

  def __str__(self):
    return self.str()


# Global stopwatch is disabled by default to not incur the performance hit if
# it's not wanted.
sw = StopWatch(enabled=False)
