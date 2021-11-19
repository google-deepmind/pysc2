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

#include "pysc2/env/converter/cc/visual_actions.h"


#include "gmock/gmock.h"
#include "gtest/gtest.h"
#include "absl/status/status.h"
#include "pysc2/env/converter/cc/check_protos_equal.h"
#include "pysc2/env/converter/cc/file_util.h"
#include "pysc2/env/converter/cc/tensor_util.h"
#include "s2clientprotocol/sc2api.pb.h"

namespace pysc2 {
namespace {

class VisualActionsTest : public testing::TestWithParam<const char*> {};

TEST_P(VisualActionsTest, DecodeEncodeTest) {
  ActionContext action_context = {48, 48, 549};

  SC2APIProtocol::Action action;
  absl::Status status =
      GetTextProto((
                       absl::StrCat("pysc2/"
                                    "env/converter/cc/test_data/actions/",
                                    GetParam())),
                   &action);
  ASSERT_TRUE(status.ok()) << status;

  // Decode the action.
  SC2APIProtocol::RequestAction request_action;
  *request_action.add_actions() = action;

  absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> decoded =
      Decode(request_action, action_context);

  // Re-encode it.
  SC2APIProtocol::RequestAction encoded;
  int func_id = ToScalar(decoded["function"]);
  const VisualAction& func = GetAction(func_id);
  if (func.action_type() != no_op) {
    // Encode action proto.
    *encoded.add_actions() = func.Encode(decoded, action_context);
  }

  absl::Status result = CheckProtosEqual(encoded, request_action);
  EXPECT_TRUE(result.ok()) << result;
}

INSTANTIATE_TEST_SUITE_P(VisualActionsTests, VisualActionsTest,
                         testing::Values("feature_camera_move.pbtxt",
                                         "feature_unit_command.pbtxt",
                                         "feature_unit_selection_point.pbtxt",
                                         "ui_control_group_append.pbtxt",
                                         "ui_control_group_recall.pbtxt"));

}  // namespace
}  // namespace pysc2
