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

#include "pysc2/env/converter/cc/visual_converter.h"

#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "absl/status/status.h"
#include "dm_env_rpc/v1/dm_env_rpc.pb.h"
#include "pysc2/env/converter/cc/check_protos_equal.h"
#include "pysc2/env/converter/cc/features.h"
#include "pysc2/env/converter/cc/tensor_util.h"
#include "pysc2/env/converter/proto/converter.pb.h"
#include "s2clientprotocol/common.pb.h"
#include "s2clientprotocol/spatial.pb.h"

namespace pysc2 {
namespace {

ConverterSettings MakeSettings() {
  ConverterSettings settings;
  settings.set_num_action_types(554);
  settings.mutable_visual_settings()->mutable_screen()->set_x(96);
  settings.mutable_visual_settings()->mutable_screen()->set_y(96);
  settings.mutable_visual_settings()->add_screen_features("height_map");
  settings.mutable_visual_settings()->add_screen_features("visibility_map");
  return settings;
}

pysc2::Observation MakePlayerObservation() {
  pysc2::Observation player_observation;

  SC2APIProtocol::FeatureLayers* screen = player_observation.mutable_player()
                                              ->mutable_observation()
                                              ->mutable_feature_layer_data()
                                              ->mutable_renders();

  SC2APIProtocol::ImageData* screen_height_map = screen->mutable_height_map();
  screen_height_map->set_bits_per_pixel(8);
  screen_height_map->mutable_size()->set_x(96);
  screen_height_map->mutable_size()->set_y(96);
  *screen_height_map->mutable_data() = std::string(96 * 96, 0);

  SC2APIProtocol::ImageData* screen_visibility_map =
      screen->mutable_visibility_map();
  screen_visibility_map->set_bits_per_pixel(8);
  screen_visibility_map->mutable_size()->set_x(96);
  screen_visibility_map->mutable_size()->set_y(96);
  *screen_visibility_map->mutable_data() = std::string(96 * 96, 0);

  return player_observation;
}

TEST(VisualConverterTest, Construct) {
  VisualConverter visual_converter(MakeSettings());
}

TEST(VisualConverterTest, FeaturePlanes) {
  VisualConverter visual_converter(MakeSettings());

  auto obs_spec = visual_converter.ObservationSpec();
  for (std::string feature : {"height_map", "visibility_map"}) {
    std::string label = absl::StrCat("screen_", feature);
    auto iter = obs_spec.find(label);
    ASSERT_TRUE(iter != obs_spec.cend()) << label;
    auto spec = iter->second;
    int range = GetScreenFeatureScale(feature).value();
    absl::Status result = CheckProtosEqual(
        spec, TensorSpec(label, dm_env_rpc::v1::DataType::UINT8, {96, 96}, 0,
                         range - 1));
    EXPECT_TRUE(result.ok()) << result;
  }

  auto converted_or =
      visual_converter.ConvertObservation(MakePlayerObservation());
  ASSERT_TRUE(converted_or.ok()) << converted_or.status();
  const auto& converted = *converted_or;

  for (std::string label : {"screen_height_map", "screen_visibility_map"}) {
    auto iter = converted.find(label);
    ASSERT_TRUE(iter != converted.cend()) << label;
    auto obs = iter->second;
    EXPECT_TRUE(obs.has_uint8s());
    EXPECT_EQ(obs.shape(0), 96) << label;
    EXPECT_EQ(obs.shape(1), 96) << label;
  }
}

}  // namespace
}  // namespace pysc2
