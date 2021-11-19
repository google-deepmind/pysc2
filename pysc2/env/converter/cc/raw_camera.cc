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

#include "pysc2/env/converter/cc/raw_camera.h"

#include <cstdint>

#include "glog/logging.h"
#include "pysc2/env/converter/cc/map_util.h"
#include "s2clientprotocol/common.pb.h"

namespace pysc2 {

namespace {

SC2APIProtocol::Point2D MakePoint(float x, float y) {
  SC2APIProtocol::Point2D point;
  point.set_x(x);
  point.set_y(y);
  return point;
}

}  // namespace

RawCamera::RawCamera(float pos_x, float pos_y, float left, float right,
                     float top, float bottom)
    : pos_x_(pos_x),
      pos_y_(pos_y),
      left_(left),
      right_(right),
      top_(top),
      bottom_(bottom) {
  CHECK_GT(left_, 0);
  CHECK_GT(right_, 0);
  CHECK_GT(top_, 0);
  CHECK_GT(bottom_, 0);
}

dm_env_rpc::v1::Tensor RawCamera::RenderCamera(
    const SC2APIProtocol::Size2DI& map_size,
    const SC2APIProtocol::Size2DI& resolution) {
  // In the game's coordinate system, points higher on the map have a lower y
  // coordinate. In the agent's coordinate system, this is inverted.
  // Translate from the game's coordinates to the agent's coordinates.
  int left =
      WorldToMinimapPx(MakePoint(pos_x_ - left_, pos_y_), map_size, resolution)
          .x();
  int right =
      WorldToMinimapPx(MakePoint(pos_x_ + right_, pos_y_), map_size, resolution)
          .x();
  int top =
      WorldToMinimapPx(MakePoint(pos_x_, pos_y_ - top_), map_size, resolution)
          .y();
  int bottom = WorldToMinimapPx(MakePoint(pos_x_, pos_y_ + bottom_), map_size,
                                resolution)
                   .y();

  // This should hold true in agent coordinates.
  CHECK_LT(left, right);
  CHECK_LT(bottom, top);

  dm_env_rpc::v1::Tensor output;
  output.add_shape(resolution.y());
  output.add_shape(resolution.x());
  for (int y = 0; y < resolution.y(); y++) {
    for (int x = 0; x < resolution.x(); x++) {
      // Note that we are lenient with the area here: We include all pixels that
      // get crossed by the camera edges.
      output.mutable_int32s()->add_array(left <= x && x <= right &&
                                         bottom <= y && y <= top);
    }
  }
  return output;
}

void RawCamera::Move(float x, float y) {
  pos_x_ = x;
  pos_y_ = y;
}

float RawCamera::X() const { return pos_x_; }
float RawCamera::Y() const { return pos_y_; }

bool RawCamera::IsOnScreen(float x, float y) const {
  float x_min = pos_x_ - left_;
  float x_max = pos_x_ + right_;
  // y_min is higher on the map than y_max.
  float y_min = pos_y_ - top_;
  float y_max = pos_y_ + bottom_;
  return x_min <= x && x <= x_max && y_min <= y && y <= y_max;
}

}  // namespace pysc2
