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

#ifndef PYSC2_ENV_CONVERTER_CC_MAP_UTIL_H_
#define PYSC2_ENV_CONVERTER_CC_MAP_UTIL_H_

#include "s2clientprotocol/common.pb.h"

namespace pysc2 {

SC2APIProtocol::PointI WorldToMinimapPx(
    const SC2APIProtocol::Point2D& point,
    const SC2APIProtocol::Size2DI& map_size,
    const SC2APIProtocol::Size2DI& raw_resolution);

SC2APIProtocol::PointI WorldToMinimapPx(
    const SC2APIProtocol::Point& point, const SC2APIProtocol::Size2DI& map_size,
    const SC2APIProtocol::Size2DI& raw_resolution);

int WorldToMinimapDistance(float distance,
                           const SC2APIProtocol::Size2DI& map_size,
                           const SC2APIProtocol::Size2DI& raw_resolution);

SC2APIProtocol::Size2DI MakeSize2DI(int x, int y);

}  // namespace pysc2

#endif  // PYSC2_ENV_CONVERTER_CC_MAP_UTIL_H_
