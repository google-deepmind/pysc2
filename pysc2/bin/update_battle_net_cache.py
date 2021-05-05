#!/usr/bin/python
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
"""Download the battle.net cache files needed by replays.

Adapted from https://github.com/ggtracker/sc2reader .
"""

import binascii
import os
import urllib

from absl import app
from absl import flags
import mpyq
from s2protocol import versions as s2versions

from pysc2 import run_configs

FLAGS = flags.FLAGS
flags.DEFINE_string("bnet_base", None,
                    "Path to a Battle.net directory to update.")

DEPOT_URL_TEMPLATE = "http://us.depot.battle.net:1119/{hash}.{type}"


def mkdirs(*paths):
  for path in paths:
    if not os.path.exists(path):
      os.makedirs(path)


def test_looks_like_battle_net(path):
  path = path.rstrip("/").rstrip("\\")
  if os.path.basename(path) != "Battle.net":
    raise ValueError("Doesn't look like a Battle.net cache:", path)
  if not os.path.isdir(os.path.join(path, "Cache")):
    raise ValueError("Missing a Cache subdirectory:", path)


def replay_paths(paths):
  """A generator yielding the full path to the replays under `replay_dir`."""
  for path in paths:
    if path.lower().endswith(".sc2replay"):
      yield path
    else:
      for f in os.listdir(path):
        if f.lower().endswith(".sc2replay"):
          yield os.path.join(path, f)


def update_battle_net_cache(replays, bnet_base):
  """Download the battle.net cache files needed by replays."""
  test_looks_like_battle_net(bnet_base)

  downloaded = 0
  failed = set()
  for replay_path in replays:
    try:
      archive = mpyq.MPQArchive(replay_path)
    except ValueError:
      print("Failed to parse replay:", replay_path)
      continue
    extracted = archive.extract()
    contents = archive.header["user_data_header"]["content"]
    header = s2versions.latest().decode_replay_header(contents)
    base_build = header["m_version"]["m_baseBuild"]
    prot = s2versions.build(base_build)

    details_bytes = (extracted.get(b"replay.details") or
                     extracted.get(b"replay.details.backup"))
    details = prot.decode_replay_details(details_bytes)

    for map_handle in details["m_cacheHandles"]:
      # server = map_handle[4:8].decode("utf-8").strip("\x00 ")
      map_hash = binascii.b2a_hex(map_handle[8:]).decode("utf8")
      file_type = map_handle[0:4].decode("utf8")

      cache_path = os.path.join(
          bnet_base, "Cache", map_hash[0:2], map_hash[2:4],
          "%s.%s" % (map_hash, file_type))

      url = DEPOT_URL_TEMPLATE.format(hash=map_hash, type=file_type)
      if not os.path.exists(cache_path) and url not in failed:
        mkdirs(os.path.dirname(cache_path))
        print(url)
        try:
          urllib.request.urlretrieve(url, cache_path)
        except urllib.error.HTTPError as e:
          print("Download failed:", e)
          failed.add(url)
        else:
          downloaded += 1
  return downloaded


def main(argv):
  replays = list(replay_paths(argv[1:]))
  bnet_base = FLAGS.bnet_base or os.path.join(run_configs.get().data_dir,
                                              "Battle.net")

  print("Updating cache:", bnet_base)
  print("Checking", len(replays), "replays")
  downloaded = update_battle_net_cache(replays, bnet_base)
  print("Downloaded", downloaded, "files")


if __name__ == "__main__":
  app.run(main)
