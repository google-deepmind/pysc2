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

#ifndef PYSC2_ENV_CONVERTER_CC_RAW_CAMERA_H_
#define PYSC2_ENV_CONVERTER_CC_RAW_CAMERA_H_

#include <cstdint>

#include "dm_env_rpc/v1/dm_env_rpc.pb.h"
#include "s2clientprotocol/common.pb.h"

namespace pysc2 {

class RawCamera {
 public:
  // NOTE: Used camera width as height for now.
  RawCamera(float pos_x, float pos_y, float left, float right, float top,
            float bottom);

  void Move(float x, float y);
  bool IsOnScreen(float x, float y) const;
  dm_env_rpc::v1::Tensor RenderCamera(
      const SC2APIProtocol::Size2DI& map_size,
      const SC2APIProtocol::Size2DI& resolution);
  float X() const;
  float Y() const;

 private:
  float pos_x_;
  float pos_y_;
  float left_;
  float right_;
  float top_;
  float bottom_;
};

}  // namespace pysc2

#endif  // PYSC2_ENV_CONVERTER_CC_RAW_CAMERA_H_
