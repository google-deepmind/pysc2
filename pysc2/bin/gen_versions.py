#!/usr/bin/python
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
"""Generate the list of versions for run_configs."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl import app
import requests

# raw version of:
# https://github.com/Blizzard/s2client-proto/blob/master/buildinfo/versions.json
VERSIONS_FILE = "https://raw.githubusercontent.com/Blizzard/s2client-proto/master/buildinfo/versions.json"


def main(argv):
  del argv  # Unused.

  versions = requests.get(VERSIONS_FILE).json()

  for v in versions:
    version_str = v["label"]
    if version_str.count(".") == 1:
      version_str += ".0"
    print('    Version("%s", %i, "%s", None),' % (
        version_str, v["base-version"], v["data-hash"]))


if __name__ == "__main__":
  app.run(main)
