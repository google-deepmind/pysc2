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
"""Named numpy arrays for easier access to the observation data.

https://docs.scipy.org/doc/numpy/user/basics.rec.html are not enough since they
actually change the type and don't interoperate well with tensorflow.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numbers
import re

import enum
import numpy as np


class NamedDict(dict):
  """A dict where you can use `d["element"]` or `d.element`."""

  def __init__(self, *args, **kwargs):
    super(NamedDict, self).__init__(*args, **kwargs)
    self.__dict__ = self


# pylint: disable=protected-access
class NamedNumpyArray(np.ndarray):
  """A subclass of ndarray that lets you give names to indices.

  This is a normal ndarray in the sense that you can always index by numbers and
  slices, though elipses don't work. Also, all elements have the same type,
  unlike a record array.

  Names should be a list of names per dimension in the ndarray shape. The names
  should be a list or tuple of strings, a namedtuple class (with names taken
  from _fields), or an IntEnum. Alternatively if you don't want to give a name
  to a particular dimension, use None. If your array only has one dimension, the
  second level of list can be skipped.

  Example usage:
    a = named_array.NamedNumpyArray([1, 3, 6], ["a", "b", "c"])
    a.a, a[1], a["c"] => 1, 3, 6
    b = named_array.NamedNumpyArray([[1, 3], [6, 8]], [["a", "b"], None])
    b.a, b[1], b["a", 1] => [1, 3], [6, 8], 3
    c = named_array.NamedNumpyArray([[1, 3], [6, 8]], [None, ["a", "b"]])
    c[0].a, b[1, 0], b[1, "b"] => 1, 6, 8
  Look at the tests for more examples including using enums and named tuples.
  """
  # Details of how to subclass an ndarray are at:
  # https://docs.scipy.org/doc/numpy-1.13.0/user/basics.subclassing.html

  def __new__(cls, values, names, *args, **kwargs):
    obj = np.array(values, *args, **kwargs)

    if len(obj.shape) == 1:
      if obj.shape[0] == 0 and names and names[0] is None:
        # Support arrays of length 0.
        names = [None]
      else:
        # Allow just a single dimension if the array is also single dimension.
        try:
          if len(names) > 1:
            names = [names]
        except TypeError:  # len of a namedtuple is a TypeError
          names = [names]

    # Validate names!
    if not isinstance(names, (list, tuple)) or len(names) != len(obj.shape):
      raise ValueError(
          "Names must be a list of length equal to the array shape: %s != %s." %
          (len(names), len(obj.shape)))
    index_names = []
    only_none = obj.shape[0] > 0
    for i, o in enumerate(names):
      if o is None:
        index_names.append(o)
      else:
        only_none = False
        if isinstance(o, enum.EnumMeta):
          for j, n in enumerate(o._member_names_):
            if j != o[n]:
              raise ValueError("Enum has holes or doesn't start from 0.")
          o = o._member_names_
        elif isinstance(o, type):  # Assume namedtuple
          try:
            o = o._fields
          except AttributeError:
            raise ValueError("Bad names. Must be None, a list of strings, "
                             "a namedtuple, or IntEnum.")
        elif isinstance(o, (list, tuple)):
          for n in o:
            if not isinstance(n, str):
              raise ValueError(
                  "Bad name, must be a list of strings, not %s" % type(n))
        else:
          raise ValueError("Bad names. Must be None, a list of strings, "
                           "a namedtuple, or IntEnum.")
        if obj.shape[i] != len(o):
          raise ValueError("Names in dimension %s is the wrong length" % i)
        index_names.append({n: j for j, n in enumerate(o)})
    if only_none:
      raise ValueError("No names given. Use a normal numpy.ndarray instead.")

    # Finally convert to a NamedNumpyArray.
    obj = obj.view(cls)
    obj._index_names = index_names  # [{name: index}, ...], dict per dimension.
    return obj

  def __array_finalize__(self, obj):
    if obj is None:
      return
    self._index_names = getattr(obj, "_index_names", None)

  def __getattr__(self, name):
    try:
      return self[name]
    except KeyError:
      raise AttributeError("Bad attribute name: %s" % name)

  def __setattr__(self, name, value):
    if name == "_index_names":  # Need special handling to avoid recursion.
      super(NamedNumpyArray, self).__setattr__(name, value)
    else:
      self.__setitem__(name, value)

  def __getitem__(self, indices):
    """Get by indexing lookup."""
    if not isinstance(indices, tuple):
      indices = (indices,)
    obj = self
    for index in indices:
      index = _get_index(obj, index)
      obj = super(NamedNumpyArray, obj).__getitem__(index)
      if isinstance(obj, np.ndarray):  # If this is a view, index the names too.
        if isinstance(index, numbers.Integral):
          obj._index_names = obj._index_names[1:]
        elif isinstance(index, slice) and self._index_names[0]:
          # Rebuild the index of names.
          names = sorted(obj._index_names[0].items(), key=lambda item: item[1])
          sliced = {n: i for i, (n, _) in enumerate(names[index])}
          obj._index_names = [sliced] + obj._index_names[1:]
    return obj

  def __setitem__(self, indices, value):
    if not isinstance(indices, tuple):
      indices = (indices,)
    obj = self
    if len(indices) > 1:
      obj = obj.__getitem(indices[:-1])
    index = _get_index(obj, indices[-1])
    super(NamedNumpyArray, obj).__setitem__(index, value)

  def __getslice__(self, i, j):  # deprecated, but still needed...
    # https://docs.python.org/2.0/ref/sequence-methods.html
    return self[max(0, i):max(0, j):]

  def __setslice__(self, i, j, seq):  # deprecated, but still needed...
    self[max(0, i):max(0, j):] = seq

  def __repr__(self):
    """A repr, parsing the original and adding the names param."""
    names = []
    for dim_names in self._index_names:
      if dim_names:
        dim_names = [n for n, _ in sorted(dim_names.items(),
                                          key=lambda item: item[1])]
        if len(dim_names) > 11:
          dim_names = dim_names[:5] + ["..."] + dim_names[-5:]
      names.append(dim_names)
    if len(names) == 1:
      names = names[0]

    # "NamedNumpyArray([1, 3, 6], dtype=int32)" ->
    # ["NamedNumpyArray", "[1, 3, 6]", ", dtype=int32"]
    matches = re.findall(r"^(\w+)\(([\d\., \n\[\]]*)(, \w+=.+)?\)$",
                         np.array_repr(self))[0]
    return "%s(%s, %s%s)" % (
        matches[0], matches[1], names, matches[2])


def _get_index(obj, index):
  """Turn a generalized index (int/slice/str) into a real index (int/slice)."""
  if isinstance(index, (numbers.Integral, slice)):
    return index
  elif isinstance(index, str):
    try:
      return obj._index_names[0][index]
    except KeyError:
      raise KeyError("Name '%s' is invalid." % index)
    except TypeError:
      raise TypeError("Trying to access an unnamed axis by name: '%s'" % index)
  else:
    raise TypeError(
        "Can't index by type: %s; only int, string or slice" % type(index))
