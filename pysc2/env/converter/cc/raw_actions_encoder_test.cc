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

#include "pysc2/env/converter/cc/raw_actions_encoder.h"

#include <functional>
#include <string>

#include "glog/logging.h"

#include "google/protobuf/util/message_differencer.h"
#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "absl/container/flat_hash_map.h"
#include "absl/status/status.h"
#include "absl/strings/numbers.h"
#include "pysc2/env/converter/cc/file_util.h"
#include "pysc2/env/converter/cc/game_data/raw_actions.h"
#include "pysc2/env/converter/cc/map_util.h"
#include "s2clientprotocol/sc2api.pb.h"

namespace dm_env_rpc {
namespace v1 {

bool operator==(const dm_env_rpc::v1::Tensor& lhs,
                const dm_env_rpc::v1::Tensor& rhs) {
  return google::protobuf::util::MessageDifferencer::Equals(lhs, rhs);
}

}  // namespace v1
}  // namespace dm_env_rpc

namespace pysc2 {
namespace {

constexpr int kMaxUnitIndex = 512;
// Indices of the units we want to select in the test.
constexpr std::array<int, 3> kTestSelection = {5, 6, 10};
constexpr int kMaxSelectionSize = 64;

SC2APIProtocol::ResponseObservation GetResponseObservation() {
  const std::string fname = (
      "pysc2/env/"
      "converter/cc/test_data/obs_data1.pbtxt");
  SC2APIProtocol::ResponseObservation obs;
  absl::Status status = GetTextProto(fname, &obs);
  EXPECT_TRUE(status.ok()) << status;
  return obs;
}

TEST(RawActionsEncoderTest, RawAutocastActions) {
  auto obs = GetResponseObservation();
  // Find one of the raw autocast functions.
  int func_idx = 0;
  for (; func_idx < RawFunctions().size(); func_idx++) {
    if (RawFunctions()[func_idx].type == RAW_AUTOCAST) {
      break;
    }
  }
  // Make sure there actually was a raw autocast function.
  EXPECT_THAT(func_idx, testing::Lt(RawFunctions().size()));

  std::vector<int> unit_tags(kTestSelection.begin(), kTestSelection.end());
  RawActionsEncoder encoder(MakeSize2DI(100, 100), kMaxUnitIndex,
                            kMaxSelectionSize, MakeSize2DI(256, 256), 500,
                            false, false);

  absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> call =
      encoder.MakeFunctionCall(func_idx, 100, 0, unit_tags, 10, 0);

  auto encoded_or = encoder.Encode(obs, call);
  ASSERT_TRUE(encoded_or.ok()) << encoded_or.status();

  const auto& raw_obs = obs.observation().raw_data();
  EXPECT_THAT(encoded_or->actions(0).action_raw().toggle_autocast().unit_tags(),
              testing::ElementsAre(raw_obs.units(kTestSelection[0]).tag(),
                                   raw_obs.units(kTestSelection[1]).tag(),
                                   raw_obs.units(kTestSelection[2]).tag()));
}

TEST(RawActionsEncoderTest, ActionRoundTrip) {
  // Uses the action encoder to do a full round trip of
  // agent action -> proto action -> agent action and compares input and output
  // for equality.
  auto obs = GetResponseObservation();

  RawActionsEncoder encoder(MakeSize2DI(100, 100), kMaxUnitIndex,
                            kMaxSelectionSize, MakeSize2DI(256, 256), 500,
                            false, false);

  std::vector<int> unit_tags(kTestSelection.begin(), kTestSelection.end());
  int tgt = unit_tags[1];

  absl::flat_hash_map<std::string,
                      absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>>
      test_cases({
          {"no_op", encoder.MakeFunctionCall(0, 0, 0, {}, 0, 0)},
          {"raw_move_camera",
           encoder.MakeFunctionCall(168, 11252, 0, {}, 0, 0)},
          {"Attack_pt", encoder.MakeFunctionCall(2, 23452, 0, unit_tags, 0, 0)},
          {"Patrol_unit",
           encoder.MakeFunctionCall(14, 0, 0, unit_tags, tgt, 0)},
          {"HoldPosition_quick",
           encoder.MakeFunctionCall(17, 0, 0, unit_tags, 0, 0)},
          {"Build_Interceptors_autocast",
           encoder.MakeFunctionCall(200, 0, 0, unit_tags, 0, 0)},
      });

  for (const auto& entry : test_cases) {
    absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> before =
        entry.second;
    auto encoded_or = encoder.Encode(obs, before);
    ASSERT_TRUE(encoded_or.ok()) << encoded_or.status();
    absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> after =
        encoder.Decode(obs, *encoded_or);

    EXPECT_EQ(before, after) << "While checking " << entry.first;
  }
}

TEST(RawActionsEncoderTest, RepeatActionRoundTrip) {
  // Testing encoder/decoder round-trips with action repeats enabled.
  auto obs = GetResponseObservation();

  RawActionsEncoder encoder(MakeSize2DI(100, 100), kMaxUnitIndex,
                            kMaxSelectionSize, MakeSize2DI(256, 256), 529,
                            false, true);

  std::vector<int> unit_tags(kTestSelection.begin(), kTestSelection.end());

  for (int num_repeats = 0; num_repeats < 3; num_repeats++) {
    absl::flat_hash_map<
        std::string, absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>>
        test_cases({
            {"Train_Zergling_quick",
             encoder.MakeFunctionCall(528, 0, 0, unit_tags, 0, num_repeats)},
            {"Train_Drone_quick",
             encoder.MakeFunctionCall(503, 0, 0, unit_tags, 0, num_repeats)},
            {"Train_Marine_quick",
             encoder.MakeFunctionCall(511, 0, 0, unit_tags, 0, num_repeats)},
            {"Train_Zealot_quick",
             encoder.MakeFunctionCall(49, 0, 0, unit_tags, 0, num_repeats)},
        });

    for (const auto& entry : test_cases) {
      std::string error_str = "While checking " + entry.first + " with " +
                              std::to_string(num_repeats) + " repeats.";
      absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> before =
          entry.second;
      auto encoded_or = encoder.Encode(obs, before);
      ASSERT_TRUE(encoded_or.ok()) << encoded_or.status();
      auto& encoded = *encoded_or;
      EXPECT_EQ(encoded.actions().size(), num_repeats + 1) << error_str;
      for (const SC2APIProtocol::Action& action : encoded.actions()) {
        EXPECT_EQ(action.action_raw().unit_command().ability_id(),
                  encoded.actions(0).action_raw().unit_command().ability_id())
            << error_str;
      }
      absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> after =
          encoder.Decode(obs, encoded);

      EXPECT_EQ(before, after) << error_str;
    }
  }
}

}  // namespace
}  // namespace pysc2
