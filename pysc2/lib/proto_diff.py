# Copyright 2019 Google Inc. All Rights Reserved.
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
"""Diff proto objects returning paths to changed attributes."""

import deepdiff

from google.protobuf import json_format

_ARRAY_PLACEHOLDER = "*"


class ProtoPath(object):
  """Path to a proto field, from the root of the proto object."""

  def __init__(self, path):
    """Initializer.

    Args:
      path: Tuple of attribute names / array indices on the path to a field.
    """
    self._path = tuple(path)

  def get_field(self, proto):
    """Returns field at this proto path, in the specified proto."""
    value = proto
    for k in self._path:
      if isinstance(k, int):
        value = value[k]
      else:
        value = getattr(value, k)

    return value

  def with_anonymous_array_indices(self):
    """Path with array indices replaced with '*' so that they compare equal."""
    return ProtoPath(
        tuple(_ARRAY_PLACEHOLDER if isinstance(t, int) else t
              for t in self._path))

  @property
  def path(self):
    return self._path

  def __lt__(self, other):
    for k1, k2 in zip(self._path, other.path):
      if k1 < k2:
        return True
      elif k1 > k2:
        return False

    return len(self._path) < len(other.path)

  def __getitem__(self, item):
    return self._path.__getitem__(item)

  def __len__(self):
    return len(self._path)

  def __eq__(self, o):
    return self._path == o.path

  def __hash__(self):
    return hash(self._path)

  def __repr__(self):
    result = ""
    for k in self._path:
      if isinstance(k, int) or k == _ARRAY_PLACEHOLDER:
        result += "[{}]".format(k)
      else:
        result += ("." if result else "") + k

    return result


class ProtoDiffs(object):
  """Summary of diffs between two protos."""

  def __init__(self, proto_a, proto_b, changed, added, removed):
    """Initializer.

    Args:
      proto_a: First proto.
      proto_b: Second proto.
      changed: List of paths to attributes which changed between the two.
      added: List of paths to attributes added from proto_a -> proto_b.
      removed: List of paths to attributes removed from proto_a -> proto_b.
    """
    self._proto_a = proto_a
    self._proto_b = proto_b
    self._changed = sorted(changed)
    self._added = sorted(added)
    self._removed = sorted(removed)

  @property
  def proto_a(self):
    return self._proto_a

  @property
  def proto_b(self):
    return self._proto_b

  @property
  def changed(self):
    return self._changed

  @property
  def added(self):
    return self._added

  @property
  def removed(self):
    return self._removed

  def all_diffs(self):
    return self.changed + self.added + self.removed

  def report(self, differencers=None, truncate_to=0):
    """Returns a string report of diffs.

    Additions and removals are identified by proto path. Changes in value are
    reported as path: old_value -> new_value by default, though this can be
    customized via the differencers argument.

    Args:
      differencers: Iterable of callable(path, proto_a, proto_b) -> str or None
        If a string is returned it is used to represent the diff between
        path.get_field(proto_a) and path.get_field(proto_b), and no further
        differencers are invoked. If None is returned by all differencers, the
        default string diff is used.
      truncate_to: Number of characters to truncate diff output values to.
        Zero, the default, means no truncation.
    """
    results = []
    for a in self._added:
      results.append("Added {}.".format(a))

    for r in self._removed:
      results.append("Removed {}.".format(r))

    for c in self._changed:
      result = None
      if differencers:
        for d in differencers:
          result = d(c, self._proto_a, self._proto_b)
          if result:
            break

      if not result:
        result = "{} -> {}".format(
            _truncate(c.get_field(self._proto_a), truncate_to),
            _truncate(c.get_field(self._proto_b), truncate_to))
      else:
        result = _truncate(result, truncate_to)

      results.append("Changed {}: {}.".format(c, result))

    if results:
      return "\n".join(results)
    else:
      return "No diffs."

  def __repr__(self):
    return "changed: {}, added: {}, removed: {}".format(
        self._changed, self._added, self._removed)


def _truncate(val, truncate_to):
  string_val = str(val)
  if truncate_to and len(string_val) > truncate_to:
    return string_val[:max(truncate_to - 3, 0)] + "..."
  else:
    return string_val


def _dict_path_to_proto_path(dict_path):
  dict_path = dict_path[5:-1]  # strip off 'root[...]'
  keys = dict_path.split("][")  # tokenize
  return ProtoPath(
      (k[1:-1] if k[0] == "'" else int(k)) for k in keys)  # key or idx


def compute_diff(proto_a, proto_b):
  """Returns `ProtoDiff` of two protos, else None if no diffs.

  Args:
    proto_a: First of the two protos to compare.
    proto_b: Second of the two protos to compare.
  """
  dict1 = json_format.MessageToDict(proto_a, preserving_proto_field_name=True)
  dict2 = json_format.MessageToDict(proto_b, preserving_proto_field_name=True)
  diff = deepdiff.DeepDiff(dict1, dict2, significant_digits=3)
  if diff:
    changed_paths = []
    for key in diff.pop("values_changed", []):
      changed_paths.append(_dict_path_to_proto_path(key))

    added_paths = []
    for key in diff.pop("dictionary_item_added", []):
      added_paths.append(_dict_path_to_proto_path(key))

    for key in diff.pop("iterable_item_added", []):
      added_paths.append(_dict_path_to_proto_path(key))

    removed_paths = []
    for key in diff.pop("dictionary_item_removed", []):
      removed_paths.append(_dict_path_to_proto_path(key))

    for key in diff.pop("iterable_item_removed", []):
      removed_paths.append(_dict_path_to_proto_path(key))

    if diff:
      raise ValueError("Unhandled diffs: {}".format(diff))

    return ProtoDiffs(
        proto_a=proto_a,
        proto_b=proto_b,
        changed=changed_paths,
        added=added_paths,
        removed=removed_paths)
  else:
    return None
