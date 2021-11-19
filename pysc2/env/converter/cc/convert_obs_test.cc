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

#include "pysc2/env/converter/cc/convert_obs.h"

#include <cstdint>


#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "absl/container/flat_hash_set.h"
#include "absl/status/status.h"
#include "pysc2/env/converter/cc/file_util.h"
#include "pysc2/env/converter/cc/game_data/proto/units.pb.h"
#include "pysc2/env/converter/cc/map_util.h"
#include "pysc2/env/converter/cc/tensor_util.h"
#include "pysc2/env/converter/proto/converter.pb.h"
#include "s2clientprotocol/spatial.pb.h"

namespace pysc2 {
namespace {

const int kNumUnitTypes = 236;
const int kNumUnitFeatures = 36;
const int kNumActionTypes = 556;
const int kAddonTypeIndex = 33;

TEST(ConvertObs, FeatureLayerFieldIndicesAreInOrderSpecified) {
  SC2APIProtocol::FeatureLayersMinimap feature_layers;
  std::vector<std::string> layer_names({"player_relative", "height_map"});
  auto indices = FeatureLayerFieldIndices(layer_names, feature_layers);
  std::vector<int, std::allocator<int>> expected = std::vector<int>({5, 0});
  EXPECT_EQ(indices, expected);
}

TEST(ConvertObsDeathTest, FeatureLayerFieldIndicesDiesIfLayerNotFound) {
  SC2APIProtocol::FeatureLayersMinimap feature_layers;
  std::vector<std::string> layer_names({"player_relative", "heght_map"});
  EXPECT_DEATH(FeatureLayerFieldIndices(layer_names, feature_layers),
               "Could not find heght_map");
}

TEST(ConvertObs, FeatureLayers8Bit) {
  const int dim = 128;
  SC2APIProtocol::FeatureLayersMinimap feature_layers;
  SC2APIProtocol::ImageData* height_map = feature_layers.mutable_height_map();
  height_map->mutable_size()->set_x(dim);
  height_map->mutable_size()->set_y(dim);
  height_map->set_bits_per_pixel(8);
  char data[dim * dim];
  for (int y = 0; y < dim; ++y) {
    for (int x = 0; x < dim; ++x) {
      data[y * dim + x] = static_cast<char>(y + x);
    }
  }
  height_map->set_data(data, dim * dim);
  auto tensor = FeatureLayer8bit(feature_layers, 0, "height_map");

  EXPECT_EQ(tensor.shape().Get(0), dim);
  EXPECT_EQ(tensor.shape().Get(1), dim);
  EXPECT_TRUE(tensor.has_uint8s());
  Matrix<uint8_t> m(tensor);
  EXPECT_EQ(m(0, 0), 0);
  EXPECT_EQ(m(dim - 1, dim - 1), dim + dim - 2);
}

TEST(ConvertObsDeathTest, FeatureLayers8BitDiesIfLayerNameMismatch) {
  const int dim = 128;
  SC2APIProtocol::FeatureLayersMinimap feature_layers;
  SC2APIProtocol::ImageData* height_map = feature_layers.mutable_height_map();
  height_map->mutable_size()->set_x(dim);
  height_map->mutable_size()->set_y(dim);
  height_map->set_bits_per_pixel(8);
  char data[dim * dim];
  for (int y = 0; y < dim; ++y) {
    for (int x = 0; x < dim; ++x) {
      data[y * dim + x] = static_cast<char>(y + x);
    }
  }
  height_map->set_data(data, dim * dim);
  EXPECT_DEATH(FeatureLayer8bit(feature_layers, 0, "player_relative"),
               "Field height_map mismatch vs player_relative");
}

TEST(ConvertObs, RawUnitsFullVecTerranAddonPopulated) {
  std::string env_recording_path = (
      "pysc2/env/"
      "converter/cc/test_data/recordings/tvt_trunk.pb");

  RecordedEpisode env_recording;
  absl::Status result = GetBinaryProto(env_recording_path, &env_recording);
  ASSERT_TRUE(result.ok()) << result;

  const SC2APIProtocol::ResponseObservation obs =
      env_recording.observations(env_recording.observations_size() - 1)
          .player();

  absl::flat_hash_set<int64_t> last_unit_tags;
  dm_env_rpc::v1::Tensor raw_units = RawUnitsFullVec(
      last_unit_tags, 0, obs.observation().raw_data(), 512, true,
      MakeSize2DI(128, 128), MakeSize2DI(256, 256), kNumUnitTypes,
      kNumUnitFeatures, true, kNumActionTypes, true, true, nullptr);

  absl::flat_hash_set<uint32_t> addons = {
      Terran::BarracksReactor, Terran::BarracksTechLab, Terran::StarportReactor,
      Terran::StarportTechLab, Terran::FactoryReactor,  Terran::FactoryTechLab};

  int num_addons = 0;
  Matrix<int32_t> m(raw_units);
  for (int i = 0; i < m.height(); i++) {
    int addon_type = m(i, kAddonTypeIndex);
    if (addon_type > 0) {
      ASSERT_TRUE(addons.find(addon_type) != addons.end());
      num_addons++;
    }
  }

  ASSERT_EQ(num_addons, 7);
}

}  // namespace
}  // namespace pysc2
