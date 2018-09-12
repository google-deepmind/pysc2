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
from future.builtins import range  # pylint: disable=redefined-builtin
import numpy as np
import six


class NamedDict(dict):
  """A dict where you can use `d["element"]` or `d.element`."""

  def __init__(self, *args, **kwargs):
    super(NamedDict, self).__init__(*args, **kwargs)
    self.__dict__ = self


_NULL_SLICE = slice(None, None, None)


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

    if len(obj.shape) == 0:  # pylint: disable=g-explicit-length-test
      raise ValueError("Scalar arrays are unsupported.")

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
            if not isinstance(n, six.string_types):
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
    indices = self._indices(indices)
    obj = super(NamedNumpyArray, self).__getitem__(indices)

    if isinstance(obj, np.ndarray):  # If this is a view, index the names too.
      if not isinstance(indices, tuple):
        indices = (indices,)
      new_names = []
      dim = 0
      for i, index in enumerate(indices):
        if isinstance(index, numbers.Integral):
          pass  # Drop this dimension's names.
        elif index is Ellipsis:
          # Copy all the dimensions' names through.
          end = len(self.shape) - len(indices) + i
          for j in range(dim, end + 1):
            new_names.append(self._index_names[j])
          dim = end
        elif (self._index_names[dim] is None or
              (isinstance(index, slice) and index == _NULL_SLICE)):
          # Keep unnamed dimensions or ones where the slice is a no-op.
          new_names.append(self._index_names[dim])
        elif isinstance(index, (slice, list, np.ndarray)):
          if isinstance(index, np.ndarray) and len(index.shape) > 1:
            raise TypeError("What does it mean to index into a named array by "
                            "a multidimensional array?")
          # Rebuild the index of names for the various forms of slicing.
          names = sorted(self._index_names[dim].items(),
                         key=lambda item: item[1])
          names = np.array(names, dtype=object)  # Support full numpy slicing.
          sliced = names[index]  # Actually slice it.
          sliced = {n: j for j, (n, _) in enumerate(sliced)}  # Reindex.
          new_names.append(sliced)
        else:
          raise TypeError("Unknown index: %s; %s" % (type(index), index))
        dim += 1
      obj._index_names = new_names + self._index_names[dim:]
      if len(obj._index_names) != len(obj.shape):
        raise IndexError("Names don't match object shape: %s != %s" % (
            len(obj.shape), len(obj._index_names)))
    return obj

  def __setitem__(self, indices, value):
    super(NamedNumpyArray, self).__setitem__(self._indices(indices), value)

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

  def __reduce__(self):
    # Support pickling: https://stackoverflow.com/a/26599346
    state = super(NamedNumpyArray, self).__reduce__()  # pytype: disable=attribute-error
    assert len(state) == 3  # Verify numpy hasn't changed their protocol.
    return (state[0], state[1], state[2] + (self._index_names,))

  def __setstate__(self, state):
    # Support pickling: https://stackoverflow.com/a/26599346
    self._index_names = state[-1]
    super(NamedNumpyArray, self).__setstate__(state[0:-1])  # pytype: disable=attribute-error

  def _indices(self, indices):
    """Turn all string indices into int indices, preserving ellipsis."""
    if isinstance(indices, tuple):
      out = []
      dim = 0
      for i, index in enumerate(indices):
        if index is Ellipsis:
          out.append(index)
          dim = len(self.shape) - len(indices) + i
        else:
          out.append(self._get_index(dim, index))
        dim += 1
      return tuple(out)
    else:
      return self._get_index(0, indices)

  def _get_index(self, dim, index):
    """Turn a string into a real index, otherwise return the index."""
    if isinstance(index, six.string_types):
      try:
        return self._index_names[dim][index]
      except KeyError:
        raise KeyError("Name '%s' is invalid for axis %s." % (index, dim))
      except TypeError:
        raise TypeError(
            "Trying to access an unnamed axis %s by name: '%s'" % (dim, index))
    else:
      return index
