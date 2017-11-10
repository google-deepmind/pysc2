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
"""A base replay parser to write custom replay data scrappers."""

import collections
import six

class BaseParser(object):
    """Summary stats of the replays seen so far."""
    def __init__(self):
        self.replays = 0
        self.steps = 0
        self.maps = collections.defaultdict(int)
        self.races = collections.defaultdict(int)
        self.crashing_replays = set()
        self.invalid_replays = set()

    def merge(self, other):
        """Merge another ReplayStats into this one."""

        def merge_dict(a, b):
            for k, v in six.iteritems(b):
                a[k] += v
        self.replays += other.replays
        self.steps += other.steps
        merge_dict(self.maps, other.maps)
        merge_dict(self.races, other.races)
        self.crashing_replays |= other.crashing_replays
        self.invalid_replays |= other.invalid_replays

    def __str__(self):
        len_sorted_dict = lambda s: (len(s), self.sorted_dict_str(s))
        len_sorted_list = lambda s: (len(s), sorted(s))
        return "\n\n".join((
        "Replays: %s, Steps total: %s" % (self.replays, self.steps),
        "Maps: %s\n%s" % len_sorted_dict(self.maps),
        "Races: %s\n%s" % len_sorted_dict(self.races),
        "Crashing replays: %s\n%s" % len_sorted_list(self.crashing_replays),
        "Invalid replays: %s\n%s" % len_sorted_list(self.invalid_replays),
        ))

    def valid_replay(self,info, ping):
        #All replays are valid in the base parser
        return True

    def parse_step(self,obs,feat):
        pass

    def sorted_dict_str(self, d):
      return "{%s}" % ", ".join("%s: %s" % (k, d[k])
                                for k in sorted(d, key=d.get, reverse=True))
