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
"""Configs for how to run SC2 from a normal install on various platforms."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import platform

from pysc2.run_configs import lib


class LocalBase(lib.RunConfig):
  """Base run config for the deepmind file hierarchy."""

  def __init__(self, base_dir, exec_path, cwd=None):
    base_dir = os.path.expanduser(base_dir)
    exec_path = os.path.join(base_dir, exec_path)
    cwd = cwd and os.path.join(base_dir, cwd)

    if "Versions/Base*/" in exec_path:
      versions = os.listdir(os.path.join(base_dir, "Versions"))
      latest = sorted(versions, key=lambda v: -int(v[4:]))[0]
      exec_path = exec_path.replace("Base*", latest)

    super(LocalBase, self).__init__(
        replay_dir=os.path.join(base_dir, "replays"),
        data_dir=base_dir, tmp_dir=None, exec_path=exec_path, cwd=cwd)


class Windows(LocalBase):

  def __init__(self):
    super(Windows, self).__init__(
        "C:/Program Files (x86)/StarCraft II",
        "Versions/Base*/SC2_x64.exe",
        "Support64")

  @classmethod
  def priority(cls):
    if platform.system() == "Windows":
      return 1


class MacOS(LocalBase):

  def __init__(self):
    super(MacOS, self).__init__(
        "/Applications/StarCraft II/",
        "Versions/Base*/SC2.app/Contents/MacOS/SC2")

  @classmethod
  def priority(cls):
    if platform.system() == "Darwin":
      return 1


class Linux(LocalBase):

  def __init__(self):
    super(Linux, self).__init__(
        "~/StarCraftII/", "Versions/Base*/SC2_x64")

  @classmethod
  def priority(cls):
    if platform.system() == "Linux":
      return 1

