// Copyright 2021 DeepMind Technologies Ltd. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS-IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include "pysc2/env/converter/cc/map_util.h"

#include <algorithm>
#include <cmath>
#include <cstdint>

#include "pysc2/env/converter/cc/castops.h"
#include "s2clientprotocol/common.pb.h"

namespace pysc2 {

SC2APIProtocol::PointI WorldToMinimapPx(
    const SC2APIProtocol::Point2D& point,
    const SC2APIProtocol::Size2DI& map_size,
    const SC2APIProtocol::Size2DI& raw_resolution) {
  float x = point.x();
  float y = map_size.y() - point.y();
  float max_dim = std::max(map_size.x(), map_size.y());
  float scale_x = raw_resolution.x() / max_dim;
  float scale_y = raw_resolution.y() / max_dim;

  SC2APIProtocol::PointI result_point;
  result_point.set_x(ToInt32(std::floor(x * scale_x)));
  result_point.set_y(ToInt32(std::floor(y * scale_y)));
  return result_point;
}

SC2APIProtocol::PointI WorldToMinimapPx(
    const SC2APIProtocol::Point& point, const SC2APIProtocol::Size2DI& map_size,
    const SC2APIProtocol::Size2DI& raw_resolution) {
  SC2APIProtocol::Point2D point2d;
  point2d.set_x(point.x());
  point2d.set_y(point.y());
  return WorldToMinimapPx(point2d, map_size, raw_resolution);
}

int WorldToMinimapDistance(float distance,
                           const SC2APIProtocol::Size2DI& map_size,
                           const SC2APIProtocol::Size2DI& raw_resolution) {
  float max_dim = std::max(map_size.x(), map_size.y());
  return ToInt32(distance * (raw_resolution.x() / max_dim));
}

SC2APIProtocol::Size2DI MakeSize2DI(int x, int y) {
  SC2APIProtocol::Size2DI size_2di;
  size_2di.set_x(x);
  size_2di.set_y(y);
  return size_2di;
}

}  // namespace pysc2
