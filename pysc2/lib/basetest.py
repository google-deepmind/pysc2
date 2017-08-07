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
"""This wraps around google.apputils.basetest for python3 compatibility."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# pylint: disable=wildcard-import,g-import-not-at-top

import six


if six.PY2:  # Google apputils only works on python 2 for now. :(
  from google.apputils.basetest import *
else:
  from pysc2.lib import app
  import unittest

  TestCase = unittest.TestCase

  def main():
    app.really_start(lambda argv: unittest.main(argv=argv))
