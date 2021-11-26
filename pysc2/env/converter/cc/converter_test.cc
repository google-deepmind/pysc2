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

#include "pysc2/env/converter/cc/converter.h"

#include <cstdint>
#include <string>

#include "glog/logging.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "absl/container/flat_hash_map.h"
#include "absl/status/status.h"
#include "absl/strings/match.h"
#include "dm_env_rpc/v1/dm_env_rpc.pb.h"
#include "pysc2/env/converter/cc/check_protos_equal.h"
#include "pysc2/env/converter/cc/game_data/raw_actions.h"
#include "pysc2/env/converter/proto/converter.pb.h"
#include "s2clientprotocol/common.pb.h"
#include "s2clientprotocol/sc2api.pb.h"
#include "s2clientprotocol/spatial.pb.h"

namespace pysc2 {
namespace {

constexpr int kNumActionTypes = 539;
constexpr int kMaxUnitCount = 16;
constexpr int kNumUnitTypes = 243;
constexpr int kNumUnitFeatures = 40;
constexpr int kNumUpgrades = 40;
constexpr int kNumUpgradeTypes = 86;
constexpr int kMaxUnitSelectionSize = 16;
constexpr int kMapSize = 128;
constexpr int kRawResolution = 128;
constexpr int kMinimapSize = 64;
constexpr int kScreenSize = 96;

template <typename T>
std::vector<std::string> GetKeys(
    const absl::flat_hash_map<std::string, T>& map) {
  std::vector<std::string> keys;
  for (const auto& [k, v] : map) {
    keys.push_back(k);
  }
  std::sort(keys.begin(), keys.end());
  return keys;
}

template <typename T>
std::vector<T> ToVector(const google::protobuf::RepeatedField<T>& repeated_field) {
  return std::vector<T>(repeated_field.cbegin(), repeated_field.cend());
}

std::vector<int> ToVector(const dm_env_rpc::v1::TensorSpec::Value& value) {
  switch (value.payload_case()) {
    case dm_env_rpc::v1::TensorSpec_Value::kInt32S:
      return ToVector<int>(value.int32s().array());
    case dm_env_rpc::v1::TensorSpec_Value::kUint8S: {
      const std::string& string = value.uint8s().array();
      const uint8_t* array = reinterpret_cast<const uint8_t*>(string.data());
      return std::vector<int>(&array[0], &array[string.length()]);
    }
    default:
      CHECK(false) << "Unhandled payload case: " << value.payload_case();
  }
}

EnvironmentInfo MakeEnvironmentInfo() {
  EnvironmentInfo environment_info;
  auto* player = environment_info.mutable_game_info()->add_player_info();
  player->set_type(SC2APIProtocol::Participant);
  auto* player2 = environment_info.mutable_game_info()->add_player_info();
  player2->set_type(SC2APIProtocol::Participant);

  auto* game_info = environment_info.mutable_game_info();
  game_info->mutable_start_raw()->mutable_map_size()->set_x(kMapSize);
  game_info->mutable_start_raw()->mutable_map_size()->set_y(kMapSize);
  return environment_info;
}

ConverterSettings MakeSettingsRaw() {
  ConverterSettings settings;
  settings.set_num_action_types(kNumActionTypes);
  settings.set_num_unit_types(kNumUnitTypes);
  settings.set_num_upgrade_types(kNumUpgradeTypes);
  settings.set_max_num_upgrades(kNumUpgrades);
  settings.mutable_minimap()->set_x(kMinimapSize);
  settings.mutable_minimap()->set_y(kMinimapSize);
  settings.add_minimap_features("height_map");
  settings.add_minimap_features("visibility_map");
  settings.set_add_opponent_features(true);
  auto* raw = settings.mutable_raw_settings();
  raw->set_max_unit_count(kMaxUnitCount);
  raw->set_num_unit_features(kNumUnitFeatures);
  raw->set_max_unit_selection_size(kMaxUnitSelectionSize);
  raw->mutable_resolution()->set_x(kRawResolution);
  raw->mutable_resolution()->set_y(kRawResolution);
  raw->set_enable_action_repeat(true);
  return settings;
}

ConverterSettings MakeSettingsVisual() {
  ConverterSettings settings;
  settings.set_num_action_types(kNumActionTypes);
  settings.set_num_unit_types(kNumUnitTypes);
  settings.set_num_upgrade_types(kNumUpgradeTypes);
  settings.set_max_num_upgrades(kNumUpgrades);
  settings.mutable_minimap()->set_x(kMinimapSize);
  settings.mutable_minimap()->set_y(kMinimapSize);
  settings.add_minimap_features("height_map");
  settings.add_minimap_features("visibility_map");
  settings.set_add_opponent_features(true);
  auto* visual = settings.mutable_visual_settings();
  visual->mutable_screen()->set_x(kScreenSize);
  visual->mutable_screen()->set_y(kScreenSize);
  visual->add_screen_features("height_map");
  visual->add_screen_features("player_relative");
  return settings;
}

dm_env_rpc::v1::Tensor MakeTensor(int value) {
  dm_env_rpc::v1::Tensor tensor;
  tensor.mutable_int32s()->add_array(value);
  return tensor;
}

absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> MakeNoOp(
    int delay = 1) {
  absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> action;
  action["function"] = MakeTensor(0);
  action["delay"] = MakeTensor(delay);
  return action;
}

Observation MakeObservation() {
  Observation observation;
  auto* obs = observation.mutable_player()->mutable_observation();
  obs->mutable_player_common()->set_player_id(1);
  auto* minimap_renders =
      obs->mutable_feature_layer_data()->mutable_minimap_renders();
  minimap_renders->mutable_height_map()->set_bits_per_pixel(8);
  minimap_renders->mutable_height_map()->mutable_size()->set_x(kMinimapSize);
  minimap_renders->mutable_height_map()->mutable_size()->set_y(kMinimapSize);
  *minimap_renders->mutable_height_map()->mutable_data() =
      std::string(kMinimapSize * kMinimapSize, 0);
  minimap_renders->mutable_visibility_map()->set_bits_per_pixel(8);
  minimap_renders->mutable_visibility_map()->mutable_size()->set_x(
      kMinimapSize);
  minimap_renders->mutable_visibility_map()->mutable_size()->set_y(
      kMinimapSize);
  *minimap_renders->mutable_visibility_map()->mutable_data() =
      std::string(kMinimapSize * kMinimapSize, 0);

  auto* renders = obs->mutable_feature_layer_data()->mutable_renders();
  renders->mutable_height_map()->set_bits_per_pixel(8);
  renders->mutable_height_map()->mutable_size()->set_x(kScreenSize);
  renders->mutable_height_map()->mutable_size()->set_y(kScreenSize);
  *renders->mutable_height_map()->mutable_data() =
      std::string(kScreenSize * kScreenSize, 0);
  renders->mutable_player_relative()->set_bits_per_pixel(8);
  renders->mutable_player_relative()->mutable_size()->set_x(kScreenSize);
  renders->mutable_player_relative()->mutable_size()->set_y(kScreenSize);
  *renders->mutable_player_relative()->mutable_data() =
      std::string(kScreenSize * kScreenSize, 0);

  return observation;
}

TEST(RawConverterTest, ActionSpec) {
  auto converter_or = MakeConverter(MakeSettingsRaw(), MakeEnvironmentInfo());
  ASSERT_TRUE(converter_or.ok()) << converter_or.status();
  auto& converter = *converter_or;
  auto action_spec = converter.ActionSpec();
  EXPECT_EQ(
      GetKeys(action_spec),
      std::vector<std::string>({"delay", "function", "queued", "repeat",
                                "target_unit_tag", "unit_tags", "world"}));

  for (const auto& [k, v] : action_spec) {
    EXPECT_EQ(k, v.name()) << k;
    EXPECT_EQ(v.dtype(), dm_env_rpc::v1::DataType::INT32) << k;
    EXPECT_EQ(ToVector(v.shape()),
              (k == "unit_tags") ? std::vector<int>({kMaxUnitSelectionSize})
                                 : std::vector<int>({}));
    EXPECT_EQ(ToVector(v.min()),
              (k == "delay") ? std::vector<int>({1}) : std::vector<int>({0}))
        << k;
  }

  for (const auto& [k, v] : std::map<std::string, int>(
           {{"queued", 1},
            {"repeat", 2},
            {"target_unit_tag", kMaxUnitCount - 1},
            {"world", kRawResolution * kRawResolution - 1},
            {"delay", 127},
            {"function", kNumActionTypes - 1}})) {
    EXPECT_EQ(ToVector(action_spec[k].max()), std::vector<int>({v})) << k;
  }
}

TEST(RawConverterTest, ConvertActionMoveCamera) {
  auto converter_or = MakeConverter(MakeSettingsRaw(), MakeEnvironmentInfo());
  ASSERT_TRUE(converter_or.ok()) << converter_or.status();
  auto& converter = *converter_or;

  absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> raw_move_camera;
  raw_move_camera["delay"] = MakeTensor(17);
  raw_move_camera["function"] = MakeTensor(168);
  raw_move_camera["world"] = MakeTensor(131);
  auto action_or = converter.ConvertAction(raw_move_camera);
  ASSERT_TRUE(action_or.ok()) << action_or.status();
  auto& action = *action_or;

  Action expected;
  expected.set_delay(17);
  auto* act = expected.mutable_request_action()->add_actions();
  auto* center = act->mutable_action_raw()
                     ->mutable_camera_move()
                     ->mutable_center_world_space();
  // Add .5 and scale by map size (which we set to be equal to raw resolution
  // for simplicity in testing)
  center->set_x(3.5);
  // Similarly, but also the y coordinate is flipped...
  center->set_y(126.5);

  absl::Status result = CheckProtosEqual(action, expected);
  EXPECT_TRUE(result.ok()) << result;
}

TEST(RawConverterTest, ConvertActionSmartUnit) {
  auto converter_or = MakeConverter(MakeSettingsRaw(), MakeEnvironmentInfo());
  ASSERT_TRUE(converter_or.ok()) << converter_or.status();
  auto& converter = *converter_or;

  absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> raw_smart_unit;
  raw_smart_unit["delay"] = MakeTensor(31);
  raw_smart_unit["function"] = MakeTensor(1);
  raw_smart_unit["queued"] = MakeTensor(0);
  raw_smart_unit["repeat"] = MakeTensor(0);
  raw_smart_unit["unit_tags"] = MakeTensor(4);
  raw_smart_unit["world"] = MakeTensor(5);
  auto action_or = converter.ConvertAction(raw_smart_unit);
  ASSERT_TRUE(action_or.ok()) << action_or.status();
  auto& action = *action_or;

  Action expected;
  expected.set_delay(31);
  auto* act = expected.mutable_request_action()->add_actions();
  auto* unit_command = act->mutable_action_raw()->mutable_unit_command();
  unit_command->set_ability_id(1);
  unit_command->add_unit_tags(4);
  unit_command->set_queue_command(false);
  // Add .5 and scale by map size (which we set to be equal to raw resolution
  // for simplicity in testing)
  unit_command->mutable_target_world_space_pos()->set_x(5.5);
  // Similarly, but also the y coordinate is flipped...
  unit_command->mutable_target_world_space_pos()->set_y(127.5);

  absl::Status result = CheckProtosEqual(action, expected);
  EXPECT_TRUE(result.ok()) << result;
}

TEST(VisualConverterTest, ActionSpec) {
  auto converter_or =
      MakeConverter(MakeSettingsVisual(), MakeEnvironmentInfo());
  ASSERT_TRUE(converter_or.ok()) << converter_or.status();
  auto& converter = *converter_or;

  auto action_spec = converter.ActionSpec();
  EXPECT_EQ(GetKeys(action_spec),
            std::vector<std::string>(
                {"build_queue_id", "control_group_act", "control_group_id",
                 "delay", "function", "minimap", "queued", "screen", "screen2",
                 "select_add", "select_point_act", "select_unit_act",
                 "select_unit_id", "select_worker", "unload_id"}));

  for (const auto& [k, v] : action_spec) {
    EXPECT_EQ(k, v.name()) << k;
    EXPECT_EQ(v.dtype(), dm_env_rpc::v1::DataType::INT32) << k;
    EXPECT_EQ(ToVector(v.shape()), std::vector<int>({})) << k;
    EXPECT_EQ(ToVector(v.min()),
              (k == "delay") ? std::vector<int>({1}) : std::vector<int>({0}))
        << k;
  }

  for (const auto& [k, v] :
       std::map<std::string, int>({{"build_queue_id", 9},
                                   {"control_group_act", 4},
                                   {"control_group_id", 9},
                                   {"minimap", kMinimapSize * kMinimapSize - 1},
                                   {"queued", 1},
                                   {"screen", kScreenSize * kScreenSize - 1},
                                   {"screen2", kScreenSize * kScreenSize - 1},
                                   {"select_add", 1},
                                   {"select_point_act", 3},
                                   {"select_unit_act", 3},
                                   {"select_unit_id", 499},
                                   {"select_worker", 3},
                                   {"unload_id", 499},
                                   {"delay", 127},
                                   {"function", kNumActionTypes - 1}})) {
    EXPECT_EQ(ToVector(action_spec[k].max()), std::vector<int>({v})) << k;
  }
}

TEST(VisualConverterTest, ConvertActionMoveCamera) {
  auto converter_or =
      MakeConverter(MakeSettingsVisual(), MakeEnvironmentInfo());
  ASSERT_TRUE(converter_or.ok()) << converter_or.status();
  auto& converter = *converter_or;

  absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> move_camera;
  move_camera["delay"] = MakeTensor(17);
  move_camera["function"] = MakeTensor(1);
  move_camera["minimap"] = MakeTensor(6);
  auto action_or = converter.ConvertAction(move_camera);
  ASSERT_TRUE(action_or.ok()) << action_or.status();
  auto& action = *action_or;

  Action expected;
  expected.set_delay(17);
  auto* act = expected.mutable_request_action()->add_actions();
  auto* center_minimap = act->mutable_action_feature_layer()
                             ->mutable_camera_move()
                             ->mutable_center_minimap();
  // Different coordinate system to raw. Not helpful!
  center_minimap->set_x(6);
  center_minimap->set_y(0);
  absl::Status result = CheckProtosEqual(action, expected);
  EXPECT_TRUE(result.ok()) << result;
}

TEST(VisualConverterTest, ConvertActionSmartScreen) {
  auto converter_or =
      MakeConverter(MakeSettingsVisual(), MakeEnvironmentInfo());
  ASSERT_TRUE(converter_or.ok()) << converter_or.status();
  auto& converter = *converter_or;

  absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> smart_screen;
  smart_screen["delay"] = MakeTensor(4);
  smart_screen["function"] = MakeTensor(451);
  smart_screen["queued"] = MakeTensor(1);
  smart_screen["screen"] = MakeTensor(333);
  auto action_or = converter.ConvertAction(smart_screen);
  ASSERT_TRUE(action_or.ok()) << action_or.status();
  auto& action = *action_or;

  Action expected;
  expected.set_delay(4);
  auto* act = expected.mutable_request_action()->add_actions();
  auto* unit_command =
      act->mutable_action_feature_layer()->mutable_unit_command();
  unit_command->set_ability_id(1);
  unit_command->set_queue_command(true);
  unit_command->mutable_target_screen_coord()->set_x(333 % kScreenSize);
  unit_command->mutable_target_screen_coord()->set_y(333 / kScreenSize);

  absl::Status result = CheckProtosEqual(action, expected);
  EXPECT_TRUE(result.ok()) << result;
}

class ConverterTest : public testing::TestWithParam<std::string> {};

TEST_P(ConverterTest, Construction) {
  bool raw = GetParam() == "raw";
  auto converter_or = MakeConverter(
      raw ? MakeSettingsRaw() : MakeSettingsVisual(), MakeEnvironmentInfo());
  ASSERT_TRUE(converter_or.ok()) << converter_or.status();
}

TEST_P(ConverterTest, ConvertActionDelay) {
  bool raw = GetParam() == "raw";
  auto converter_or = MakeConverter(
      raw ? MakeSettingsRaw() : MakeSettingsVisual(), MakeEnvironmentInfo());
  ASSERT_TRUE(converter_or.ok()) << converter_or.status();
  auto& converter = *converter_or;

  for (int delay = 1; delay < 127; ++delay) {
    auto action_or = converter.ConvertAction(MakeNoOp(/*delay=*/delay));
    ASSERT_TRUE(action_or.ok()) << action_or.status();
    EXPECT_EQ(action_or->delay(), delay);
  }
}

TEST_P(ConverterTest, ObservationSpec) {
  bool raw = GetParam() == "raw";
  auto converter_or = MakeConverter(
      raw ? MakeSettingsRaw() : MakeSettingsVisual(), MakeEnvironmentInfo());
  ASSERT_TRUE(converter_or.ok()) << converter_or.status();
  auto& converter = *converter_or;

  auto obs_spec = converter.ObservationSpec();
  auto expected_fields = std::vector<std::string>(
      {"available_actions", "away_race_observed", "away_race_requested",
       "game_loop", "home_race_requested", "minimap_height_map",
       "minimap_visibility_map", "mmr", "opponent_player",
       "opponent_unit_counts_bow", "opponent_upgrades_fixed_length", "player",
       "raw_units", "screen_height_map", "screen_player_relative",
       "unit_counts_bow", "upgrades_fixed_length"});

  if (raw) {
    for (const auto& k :
         {"available_actions", "screen_height_map", "screen_player_relative"}) {
      expected_fields.erase(
          std::find(expected_fields.begin(), expected_fields.end(), k));
    }
  } else {
    expected_fields.erase(
        std::find(expected_fields.begin(), expected_fields.end(), "raw_units"));
  }

  EXPECT_EQ(GetKeys(obs_spec), expected_fields);

  for (const auto& [k, v] : obs_spec) {
    EXPECT_EQ(k, v.name());
    if (absl::StartsWith(k, "minimap_") || absl::StartsWith(k, "screen_")) {
      EXPECT_EQ(v.dtype(), dm_env_rpc::v1::DataType::UINT8) << k;
    } else {
      EXPECT_EQ(v.dtype(), dm_env_rpc::v1::DataType::INT32) << k;
      if (!absl::StrContains(k, "upgrades_fixed_length") &&
          !absl::StrContains(k, "raw_units")) {
        EXPECT_FALSE(v.has_min()) << k;
        EXPECT_FALSE(v.has_max()) << k;
      }
    }
  }

  for (const auto& [k, v] : std::map<std::string, int>(
           {{"minimap_height_map", 255},
            {"minimap_visibility_map", 3},
            // TODO(prichard) - This seems wrong. If 0 is 'no upgrade', max
            // would still only be kNumUpgradeTypes. Also, num upgrade types
            // only appears to be used for the spec, so isn't blocking new
            // upgrades being observed.
            {"upgrades_fixed_length", kNumUpgradeTypes + 1},
            {"opponent_upgrades_fixed_length", kNumUpgradeTypes + 1}})) {
    EXPECT_EQ(ToVector(obs_spec[k].min()), std::vector<int>({0})) << k;
    EXPECT_EQ(ToVector(obs_spec[k].max()), std::vector<int>({v})) << k;
  }

  if (!raw) {
    for (const auto& [k, v] : std::map<std::string, int>(
             {{"screen_height_map", 255}, {"screen_player_relative", 4}})) {
      EXPECT_EQ(ToVector(obs_spec[k].min()), std::vector<int>({0})) << k;
      EXPECT_EQ(ToVector(obs_spec[k].max()), std::vector<int>({v})) << k;
    }
  }

  for (const auto& f : {"away_race_observed", "away_race_requested",
                        "game_loop", "home_race_requested"}) {
    EXPECT_EQ(ToVector<int32_t>(obs_spec[f].shape()), std::vector<int>({1}))
        << f;
  }
  EXPECT_EQ(ToVector(obs_spec["mmr"].shape()), std::vector<int>({}));
  for (const auto& [k, v] : std::map<std::string, int>(
           {{"player", 11},
            {"opponent_player", 10},
            {"unit_counts_bow", kNumUnitTypes},
            {"opponent_unit_counts_bow", kNumUnitTypes},
            {"upgrades_fixed_length", kNumUpgrades},
            {"opponent_upgrades_fixed_length", kNumUpgrades}})) {
    EXPECT_EQ(ToVector(obs_spec[k].shape()), std::vector<int>({v}));
  }

  if (raw) {
    EXPECT_EQ(ToVector(obs_spec["raw_units"].shape()),
              std::vector<int>({kMaxUnitCount, kNumUnitFeatures + 2}));
  } else {
    EXPECT_EQ(ToVector(obs_spec["available_actions"].shape()),
              std::vector<int>({kNumActionTypes}));
  }
}

TEST_P(ConverterTest, ObservationMatchesSpec) {
  bool raw = GetParam() == "raw";
  auto converter_or = MakeConverter(
      raw ? MakeSettingsRaw() : MakeSettingsVisual(), MakeEnvironmentInfo());
  ASSERT_TRUE(converter_or.ok()) << converter_or.status();
  auto& converter = *converter_or;

  auto obs_spec = converter.ObservationSpec();
  auto converted_or = converter.ConvertObservation(MakeObservation());
  ASSERT_TRUE(converted_or.ok()) << converted_or.status();
  auto& converted = *converted_or;

  for (const auto& [k, v] : obs_spec) {
    auto iter = converted.find(k);
    EXPECT_TRUE(iter != converted.cend()) << k;
    EXPECT_EQ(ToVector<int>(iter->second.shape()), ToVector<int>(v.shape()))
        << k;
  }

  for (const auto& [k, _] : converted) {
    EXPECT_TRUE(obs_spec.find(k) != obs_spec.cend()) << k;
  }
}

INSTANTIATE_TEST_SUITE_P(ConverterTests, ConverterTest,
                         testing::Values("raw", "visual"));

}  // namespace
}  // namespace pysc2
