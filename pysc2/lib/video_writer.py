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
# See the License for the specific language gwritererning permissions and
# limitations under the License.
"""Write a video based on a numpy array."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import skvideo.io


class VideoWriter(skvideo.io.FFmpegWriter):
  """Write a video based on a numpy array.

  Subclass/wrap FFmpegWriter to make it easy to switch to a different library.
  """

  def __init__(self, filename, frame_rate):
    super(VideoWriter, self).__init__(
        filename, outputdict={"-r": str(frame_rate)})

  def add(self, frame):
    """Add a frame to the video based on a numpy array."""
    self.writeFrame(frame)

  def __del__(self):
    self.close()

