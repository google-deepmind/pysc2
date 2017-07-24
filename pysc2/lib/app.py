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
"""This is a wrapper around google.apputils.app for python3 compatibility."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# pylint: disable=wildcard-import,g-import-not-at-top

import sys

import six


if six.PY2:  # Google apputils only works on python 2 for now. :(
  from google.apputils.app import *
else:
  import gflags as flags

  flags.DEFINE_bool("help", False, "Ask for the help text.")
  flags.DEFINE_bool("helpfull", False, "Ask for the full help text.")
  FLAGS = flags.FLAGS

  def _usage():
    if not FLAGS.help and not FLAGS.helpfull:
      return
    print(sys.modules["__main__"].__doc__, "\n")
    print("USAGE:", sys.argv[0], "[flags]")
    print(str(FLAGS) if FLAGS.helpfull else FLAGS.main_module_help())
    sys.exit()

  def run():
    really_start(sys.modules["__main__"].main)

  def really_start(main=None):
    argv = FLAGS(sys.argv)
    _usage()
    sys.exit(main(argv))
