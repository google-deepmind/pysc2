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

#ifndef PYSC2_ENV_CONVERTER_CC_CONVERT_OBS_H_
#define PYSC2_ENV_CONVERTER_CC_CONVERT_OBS_H_

#include <cstdint>
#include <string>
#include <vector>

#include "glog/logging.h"
#include "google/protobuf/repeated_field.h"
#include "absl/container/flat_hash_set.h"
#include "dm_env_rpc/v1/dm_env_rpc.pb.h"
#include "pysc2/env/converter/cc/encode_image_data.h"
#include "pysc2/env/converter/cc/game_data/uint8_lookup.h"
#include "pysc2/env/converter/cc/raw_camera.h"
#include "pysc2/env/converter/cc/tensor_util.h"
#include "s2clientprotocol/common.pb.h"
#include "s2clientprotocol/sc2api.pb.h"

namespace pysc2 {

constexpr int kNumPlayerFeatures = 11;

dm_env_rpc::v1::Tensor GameLoop(const SC2APIProtocol::Observation& observation);
dm_env_rpc::v1::Tensor PlayerCommon(const SC2APIProtocol::Observation& obs);
dm_env_rpc::v1::Tensor MapPlayerIdToOne(const dm_env_rpc::v1::Tensor& player);
dm_env_rpc::v1::Tensor Upgrades(const SC2APIProtocol::Observation& obs);
dm_env_rpc::v1::Tensor UpgradesUint8FixedLength(
    const dm_env_rpc::v1::Tensor& upgrades, int max_num_upgrades);

dm_env_rpc::v1::TensorSpec RawUnitsSpec(int max_unit_count, int num_unit_types,
                                        int num_unit_features,
                                        int num_action_types);

dm_env_rpc::v1::Tensor RawUnitsFullVec(
    const absl::flat_hash_set<int64_t>& last_unit_tags,
    const int64_t last_target_unit_tag,
    const SC2APIProtocol::ObservationRaw& raw, int max_unit_count, bool is_raw,
    const SC2APIProtocol::Size2DI& map_size,
    const SC2APIProtocol::Size2DI& raw_resolution, int num_unit_types,
    int num_unit_features, bool mask_offscreen_enemies, int num_action_types,
    bool add_effects_to_units, bool add_cargo_to_units, RawCamera* camera);

dm_env_rpc::v1::Tensor RawUnitsToUint8(const dm_env_rpc::v1::Tensor& tensor,
                                       int num_unit_features);

dm_env_rpc::v1::Tensor CameraPosition(
    const SC2APIProtocol::Observation& obs,
    const SC2APIProtocol::Size2DI& map_size,
    const SC2APIProtocol::Size2DI& raw_resolution, RawCamera* camera);

dm_env_rpc::v1::Tensor CameraSize(const SC2APIProtocol::Size2DI& raw_resolution,
                                  const SC2APIProtocol::Size2DI& map_size,
                                  int camera_width_world_units);

dm_env_rpc::v1::Tensor SeparateCamera(
    const dm_env_rpc::v1::Tensor& camera_position,
    const dm_env_rpc::v1::Tensor& camera_size,
    const SC2APIProtocol::Size2DI& raw_resolution);

int GetUnitTypeIndex(int unit_type_id, bool using_uint8_unit_ids);

dm_env_rpc::v1::Tensor UnitCounts(const SC2APIProtocol::Observation& obs,
                                  bool include_hallucinations = true,
                                  bool only_count_finished_units = false);

dm_env_rpc::v1::Tensor AddUnitCountsBowData(
    const dm_env_rpc::v1::Tensor& unit_counts, int num_unit_types,
    bool using_uint8_unit_ids);

template <typename T>
dm_env_rpc::v1::Tensor UnitToUint8Matrix(const dm_env_rpc::v1::Tensor& tensor,
                                         int unit_type_index) {
  dm_env_rpc::v1::Tensor output = tensor;
  MutableMatrix<T> m(&output);
  for (int i = 0; i < m.height(); ++i) {
    m(i, unit_type_index) = PySc2ToUint8(m(i, unit_type_index));
  }
  return output;
}

template <typename T>
std::vector<int> FeatureLayerFieldIndices(
    const std::vector<std::string>& layer_names, const T& feature_layers) {
  CHECK(!layer_names.empty());
  const google::protobuf::Descriptor* descriptor = feature_layers.GetDescriptor();

  std::vector<int> field_indices;
  for (const std::string& layer_name : layer_names) {
    int i;
    for (i = 0; i < descriptor->field_count(); ++i) {
      const google::protobuf::FieldDescriptor* field = descriptor->field(i);
      if (field->name() == layer_name) {
        field_indices.push_back(i);
        break;
      }
    }

    CHECK(i != descriptor->field_count())
        << "Could not find " << layer_name << " in descriptor "
        << descriptor->DebugString();
  }
  return field_indices;
}

template <typename T>
dm_env_rpc::v1::Tensor FeatureLayer8bit(const T& layers, int layer_index,
                                        const std::string& layer_name) {
  const SC2APIProtocol::ImageData& height_map = layers.height_map();
  CHECK_GT(height_map.size().x(), 0)
      << "We expect height_map to always be present in the feature planes";
  CHECK_GT(height_map.size().y(), 0)
      << "We expect height_map to always be present in the feature planes";
  dm_env_rpc::v1::Tensor output =
      ZeroMatrix<uint8_t>(height_map.size().y(), height_map.size().x());

  const google::protobuf::Descriptor* desc = layers.GetDescriptor();
  const google::protobuf::Reflection* refl = layers.GetReflection();
  const google::protobuf::FieldDescriptor* field = desc->field(layer_index);
  CHECK(field->name() == layer_name)
      << "Field " << field->name() << " mismatch vs " << layer_name;
  const auto& layer = dynamic_cast<const SC2APIProtocol::ImageData&>(
      refl->GetMessage(layers, field));

  EncodeImageData<uint8_t>(layer,
                           (field->name() == "unit_type" ? PySc2ToUint8
                            : field->name() == "buffs"   ? PySc2ToUint8Buffs
                                                         : nullptr),
                           &output);
  return output;
}

}  // namespace pysc2

#endif  // PYSC2_ENV_CONVERTER_CC_CONVERT_OBS_H_
