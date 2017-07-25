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
"""Accept a positional argument when using the flags library."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys


def positional_flag(name, flag, argv):
  if flag is not None and len(argv) == 1:
    return flag
  if len(argv) == 2:
    return argv[1]
  if len(argv) == 1:
    sys.exit("%s is required as either a flag or positional argument" % name)
  sys.exit("Unexpected arguments that broke flag/argument parsing. "
           "Make sure all positional arguments are after all named flags.")

