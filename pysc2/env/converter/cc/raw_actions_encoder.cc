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

#include <algorithm>
#include <cstdint>
#include <utility>
#include <vector>

#include "glog/logging.h"
#include "absl/container/flat_hash_map.h"
#include "absl/container/flat_hash_set.h"
#include "absl/random/random.h"
#include "absl/status/status.h"
#include "absl/strings/str_cat.h"
#include "pysc2/env/converter/cc/game_data/raw_actions.h"
#include "pysc2/env/converter/cc/tensor_util.h"
#include "s2clientprotocol/common.pb.h"
#include "s2clientprotocol/raw.pb.h"
#include "s2clientprotocol/sc2api.pb.h"

namespace pysc2 {
namespace {

class AbilityIdToGameIdTable {
 public:
  AbilityIdToGameIdTable() {
    for (int i = 0; i < RawFunctions().size(); i++) {
      if (int ability_id = RawFunctions().at(i).ability_id; ability_id >= 0) {
        raw_ability_ids_[ability_id].push_back(i);
      }
    }
  }

  int Lookup(int ability_id) const {
    if (auto it = raw_ability_ids_.find(ability_id);
        it != raw_ability_ids_.end()) {
      const std::vector<int>& ids = it->second;
      if (auto mt = std::min_element(ids.begin(), ids.end()); mt != ids.end()) {
        return *mt;
      }
    }
    return 0;
  }

 private:
  absl::flat_hash_map<int, std::vector<int>> raw_ability_ids_;
};

int64_t FindOriginalTag(int position,
                        const SC2APIProtocol::ObservationRaw& obs) {
  if (position >= obs.units_size()) {
    // Assume it's a real unit tag.
    return position;
  } else {
    // Assume it's an index.
    return obs.units(position).tag();
  }
}

// Returns the list of unit tags selected by an agent.
std::vector<int64_t> LookupSelectedUnitTags(
    const SC2APIProtocol::ObservationRaw& obs, const std::vector<int>& indices,
    int max_possible_index) {
  std::vector<int64_t> out;
  for (int index : indices) {
    // The last index is an end of sequence symbol and gets ignored.
    if (index == max_possible_index) {
      continue;
    }

    if (index < 0) {
      LOG(WARNING) << "Invalid selection_index: " << index << " < 0";
      return out;
    }
    out.push_back(FindOriginalTag(index, obs));
  }
  return out;
}

// Infers the corresponding agent function index from a game action ability_id.
int FindFunction(int ability_id, RawFunctionType type,
                 bool map_to_general = true) {
  int function_idx;
  for (function_idx = 0; function_idx < RawFunctions().size(); function_idx++) {
    const RawFunction& f = RawFunctions()[function_idx];
    if (f.ability_id == ability_id) {
      // Some actions are "special" versions of a more general action.
      // We want to map special actions to general ones.
      // We use the fact that the general_id of a general action is 0.
      // Otherwise we need an exact match of the function type.
      if (map_to_general && f.general_id) {
        // Set map_to_general to false, in case we have a buggy function list.
        return FindFunction(f.general_id, type, false);
      } else if (f.type == type) {
        return function_idx;
      }
    }
  }

  // We did not find an ability with the given id and return a no-op.
  LOG(ERROR) << "No function found with ability " << ability_id;
  return 0;  // no-op.
}

// Inverse of LookupSelectionTags.
template <typename Container>
std::vector<int> FindSelectionIndices(const SC2APIProtocol::ObservationRaw& obs,
                                      const Container& container) {
  // Handle "unit_tags" argument.
  absl::flat_hash_set<int64_t> selected_unit_tags(container.begin(),
                                                  container.end());
  std::vector<int> unit_indices;
  unit_indices.reserve(selected_unit_tags.size());
  for (int i = 0; i < obs.units_size(); i++) {
    if (selected_unit_tags.find(obs.units(i).tag()) !=
        selected_unit_tags.end()) {
      unit_indices.push_back(i);
    }
  }
  return unit_indices;
}

template <typename V>
std::string KeysString(const absl::flat_hash_map<std::string, V>& map) {
  std::string out;
  for (const auto& [k, v] : map) {
    if (!out.empty()) {
      absl::StrAppend(&out, ", ");
    }
    absl::StrAppend(&out, k);
  }
  return out;
}

}  // namespace

absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>
RawActionsEncoder::MakeFunctionCall(int function_id, int world, int queued,
                                    const std::vector<int>& unit_tags,
                                    int target_unit_tag, int repeat) const {
  absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> call;
  call["function"] = MakeTensor(function_id);
  call["world"] = MakeTensor(world);
  call["queued"] = MakeTensor(queued);
  dm_env_rpc::v1::Tensor tensor;
  tensor.add_shape(max_selection_size_);
  for (int i = 0; i < max_selection_size_; i++) {
    int data;
    if (i < unit_tags.size()) {
      data = unit_tags[i];
    } else {
      // Simulate a quirk of the Python implementation:
      // When we encounter a no_op, we fill the list with zeros instead of the
      // max unit index.
      data = function_id == 0 ? 0 : max_unit_count_;
    }
    tensor.mutable_int32s()->add_array(data);
  }
  call["unit_tags"] = tensor;
  call["target_unit_tag"] = MakeTensor(target_unit_tag);

  if (action_repeat_) {
    call["repeat"] = MakeTensor(repeat);
  }

  return call;
}

RawActionsEncoder::RawActionsEncoder(
    const SC2APIProtocol::Size2DI& map_size, int max_unit_count,
    int max_selection_size, const SC2APIProtocol::Size2DI& raw_resolution,
    int num_action_types, bool shuffle_unit_tags, bool action_repeat)
    : map_size_(map_size),
      max_unit_count_(max_unit_count),
      max_selection_size_(max_selection_size),
      raw_resolution_(raw_resolution),
      num_action_types_(num_action_types),
      shuffle_unit_tags_(shuffle_unit_tags),
      action_repeat_(action_repeat) {
  CHECK_GT(map_size_.x(), 0)
      << "Please pass the game's map_size when using the raw converter. This "
         "should be in the game info returned by the SC2 API.";
  CHECK_GT(map_size_.y(), 0)
      << "Please pass the game's map_size when using the raw converter. This "
         "should be in the game info returned by the SC2 API.";
  CHECK_GT(max_unit_count_, 0);
  CHECK_GT(raw_resolution_.x(), 0)
      << "Please specify resolution in raw_settings.";
  CHECK_EQ(raw_resolution_.x(), raw_resolution_.y())
      << "Only square raw resolution is supported currently.";
  CHECK_GT(num_action_types_, 0);
}

absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>
RawActionsEncoder::Decode(
    const SC2APIProtocol::ResponseObservation& observation,
    const SC2APIProtocol::RequestAction& actions) const {
  for (const SC2APIProtocol::Action& action : actions.actions()) {
    if (!action.has_action_raw()) {
      continue;
    }

    const SC2APIProtocol::ActionRaw& action_raw = action.action_raw();
    int function_idx = 0;
    int world = 0;
    int queued = 0;
    std::vector<int> unit_indices;
    int target_unit_index = 0;
    const auto& obs = observation.observation().raw_data();

    if (action_raw.has_unit_command()) {
      const auto& cmd = action_raw.unit_command();

      RawFunctionType type = RAW_CMD;
      if (cmd.has_target_unit_tag()) {
        type = RAW_CMD_UNIT;
      } else if (cmd.has_target_world_space_pos()) {
        type = RAW_CMD_PT;
      }

      // Handle "function_id".
      function_idx = FindFunction(cmd.ability_id(), type);

      // Handle "target_unit_tag" argument.
      if (action_raw.unit_command().has_target_unit_tag()) {
        bool found = false;
        for (int i = 0; i < obs.units_size(); i++) {
          if (action_raw.unit_command().target_unit_tag() ==
              obs.units(i).tag()) {
            target_unit_index = i;
            found = true;
            break;
          }
        }
        if (!found) {
          // The unit targeted by this action doesn't exist (yet).
          // We skip such actions completely.
          continue;
        }
      }

      // Handle "world" argument.
      if (action_raw.unit_command().has_target_world_space_pos()) {
        world = WorldCoordsToAgentCoords(
            action_raw.unit_command().target_world_space_pos());
      }

      // Handle "unit_tags" argument.
      unit_indices = FindSelectionIndices(obs, cmd.unit_tags());

      // Handle "queued" argument.
      queued = action_raw.unit_command().queue_command() ? 1 : 0;
    } else if (action_raw.has_camera_move()) {
      for (function_idx = 0; function_idx < RawFunctions().size();
           function_idx++) {
        // There is only one RAW_MOVE_CAMERA function.
        if (RawFunctions()[function_idx].type == RAW_MOVE_CAMERA) {
          break;
        }
      }
      CHECK_GT(function_idx, 0) << "No RAW_MOVE_CAMERA function found";

      SC2APIProtocol::Point p = action_raw.camera_move().center_world_space();
      SC2APIProtocol::Point2D p2d;
      p2d.set_x(p.x());
      p2d.set_y(p.y());
      world = WorldCoordsToAgentCoords(p2d);
    } else if (action_raw.has_toggle_autocast()) {
      const auto& cmd = action_raw.toggle_autocast();
      // Handle "function_id".
      function_idx = FindFunction(cmd.ability_id(), RAW_AUTOCAST);
      // Handle "unit_tags" argument.
      unit_indices = FindSelectionIndices(obs, cmd.unit_tags());
    }

    if (function_idx >= num_action_types_) {
      // We are not supposed to know about this function, so ignore it.
      continue;
    }

    // Remove non-addressable units from the selection.
    unit_indices.erase(
        std::remove_if(unit_indices.begin(), unit_indices.end(),
                       [this](int i) { return i >= max_unit_count_; }),
        unit_indices.end());

    // Actions with empty unit tags / target unit tags need to be rejected, but
    // not for camera moves.
    if (!action_raw.has_camera_move()) {
      if (unit_indices.empty()) {
        // This means that no addressable unit was selected in this action, so
        // we ignore the entire action.
        continue;
      }
      if (target_unit_index >= max_unit_count_) {
        // Target unit is outside of the list of addressable units, so we ignore
        // this entire action.
        continue;
      }
    }

    if (shuffle_unit_tags_) {
      std::shuffle(unit_indices.begin(), unit_indices.end(), bit_gen_);
    }

    // If we are returning this function to the agent, it better not break any
    // of these invariants, or else things will break on the learner, and we
    // don't want that.
    CHECK_GE(function_idx, 0);
    CHECK_LT(function_idx, num_action_types_);
    CHECK_GE(world, 0);
    CHECK_LT(world, raw_resolution_.x() * raw_resolution_.y());
    CHECK_GE(queued, 0);
    CHECK_LE(queued, 1);
    for (int i = 0; i < unit_indices.size(); i++) {
      CHECK_GE(unit_indices[i], 0) << "At selection index " << i;
      CHECK_LT(unit_indices[i], max_unit_count_) << "At selection index " << i;
    }
    CHECK_GE(target_unit_index, 0);

    // Count the number of actions this frame with the same ability_id.
    int num_actions = 0;
    if (action_raw.has_unit_command()) {
      for (const SC2APIProtocol::Action& other_action : actions.actions()) {
        if (other_action.action_raw().unit_command().ability_id() ==
            action_raw.unit_command().ability_id()) {
          num_actions++;
        }
      }
    } else {
      num_actions = 1;
    }

    num_actions = std::min(num_actions, 3);

    return MakeFunctionCall(function_idx, world, queued, unit_indices,
                            target_unit_index, num_actions - 1);
  }

  // No raw actions found. Return a NO_OP.
  return MakeFunctionCall(0, 0, 0, {}, 0, 0);
}

absl::StatusOr<SC2APIProtocol::RequestAction> RawActionsEncoder::Encode(
    const SC2APIProtocol::ResponseObservation& observation,
    const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& action)
    const {
  // Input: (function, arguments=(world, queued, unit_tags, target_unit_tag))

  SC2APIProtocol::RequestAction output;

  auto function = action.find("function");
  if (function == action.cend()) {
    return absl::InvalidArgumentError(
        "`function` must be specified on all actions.");
  }
  int m_action_index = ToScalar(function->second);

  const SC2APIProtocol::ObservationRaw& raw_obs =
      observation.observation().raw_data();

  if (m_action_index < 0 || m_action_index >= RawFunctions().size()) {
    LOG(WARNING) << "Invalid action_index: " << m_action_index;
    return output;
  }
  const RawFunction& f = RawFunctions().at(m_action_index);
  if (f.type == NO_OP) {
    VLOG(1) << "Encoded a NO_OP";
    return output;
  }

  SC2APIProtocol::Action out;
  if (f.type == RAW_MOVE_CAMERA) {
    // Uses a 3D point, but we don't set z (to match Python).
    SC2APIProtocol::Point* coordinates = out.mutable_action_raw()
                                             ->mutable_camera_move()
                                             ->mutable_center_world_space();
    SC2APIProtocol::Point2D point2d;
    if (auto it = action.find("world"); it != action.cend()) {
      point2d = AgentCoordsToWorldCoords(ToScalar(it->second));
    } else {
      return absl::InvalidArgumentError(
          "`world` must be specified for raw move camera.");
    }
    coordinates->set_x(point2d.x());
    coordinates->set_y(point2d.y());
    *output.add_actions() = std::move(out);
    VLOG(1) << "Encoding raw camera move: " << output;
    return output;
  }

  // If the action is neither NO_OP nor MOVE_CAMERA, then we need to send the
  // selected unit tags.
  std::vector<int64_t> selected_tags;
  if (auto it = action.find("unit_tags"); it != action.cend()) {
    selected_tags =
        LookupSelectedUnitTags(raw_obs, ToVector(it->second), max_unit_count_);
  } else {
    return absl::InvalidArgumentError(absl::StrCat(
        "Action requires `unit_tags`, but has keys ", KeysString(action),
        ", function is ", function->second.DebugString()));
  }

  if (f.type == RAW_AUTOCAST) {
    SC2APIProtocol::ActionRawToggleAutocast* action =
        out.mutable_action_raw()->mutable_toggle_autocast();
    action->set_ability_id(f.ability_id);
    for (int64_t tag : selected_tags) {
      action->add_unit_tags(tag);
    }
    *output.add_actions() = std::move(out);
    VLOG(1) << "Encoding raw autocast: " << output;
    return output;
  }

  SC2APIProtocol::ActionRawUnitCommand* command =
      out.mutable_action_raw()->mutable_unit_command();

  command->set_ability_id(f.ability_id);
  if (auto it = action.find("queued"); it != action.cend()) {
    command->set_queue_command(ToScalar(it->second) != 0);
  } else {
    return absl::InvalidArgumentError(
        "`queued` must be specified for this action.");
  }
  for (int64_t tag : selected_tags) {
    command->add_unit_tags(tag);
  }

  if (f.type == RAW_CMD_PT) {
    int target_pos;
    if (auto it = action.find("world"); it != action.cend()) {
      target_pos = ToScalar(it->second);
    } else {
      return absl::InvalidArgumentError(
          "`world` must be specified for raw command point.");
    }
    SC2APIProtocol::Point2D* p = command->mutable_target_world_space_pos();
    *p = AgentCoordsToWorldCoords(target_pos);
  } else if (f.type == RAW_CMD_UNIT) {
    int target_index;
    if (auto it = action.find("target_unit_tag"); it != action.cend()) {
      target_index = ToScalar(it->second);
    } else {
      return absl::InvalidArgumentError(
          "`target_unit_tag` must be specified for raw command unit.");
    }
    if (target_index < 0) {
      LOG(WARNING) << "Invalid target_index: " << target_index << " < 0";
      return output;
    }
    command->set_target_unit_tag(FindOriginalTag(target_index, raw_obs));
  }

  int num_actions = -1;
  if (action_repeat_) {
    if (auto it = action.find("repeat"); it != action.cend()) {
      num_actions = ToScalar(it->second) + 1;
    } else {
      return absl::InvalidArgumentError(
          "Action repeat is enabled so `repeat` must be specified on action.");
    }

  } else {
    num_actions = 1;
  }
  if (f.type != RAW_CMD) {
    // Action repeat is currently only supported for RAW_CMD actions.
    num_actions = 1;
  }
  for (int i = 0; i < num_actions; i++) {
    *output.add_actions() = out;
  }

  VLOG(1) << "Encoded action at game loop "
          << observation.observation().game_loop() << ":\n"
          << output;

  return output;
}

SC2APIProtocol::Point2D RawActionsEncoder::AgentCoordsToWorldCoords(
    int target_pos) const {
  SC2APIProtocol::Point2D p;
  float x = target_pos % raw_resolution_.x() + 0.5;
  float y = target_pos / raw_resolution_.x() + 0.5;
  float scale = static_cast<float>(raw_resolution_.x()) /
                std::max(map_size_.x(), map_size_.y());
  p.set_x(x / scale);
  p.set_y(map_size_.y() - (y / scale));
  return p;
}

int RawActionsEncoder::WorldCoordsToAgentCoords(
    const SC2APIProtocol::Point2D& position) const {
  float scale = static_cast<float>(raw_resolution_.x()) /
                std::max(map_size_.x(), map_size_.y());
  int x = scale * position.x();
  int y = scale * (map_size_.y() - std::max(0.5f, position.y()));
  return raw_resolution_.x() * y + x;
}

void PrintAllActions() {
  for (int i = 0; i < RawFunctions().size(); i++) {
    const RawFunction& f = RawFunctions().at(i);
    LOG(INFO) << i << ": " << f.type << " " << f.label << " " << f.ability_id;
  }
}

int RawAbilityToGameId(int ability_id) {
  static AbilityIdToGameIdTable* lookup_table = new AbilityIdToGameIdTable;
  return lookup_table->Lookup(ability_id);
}

}  // namespace pysc2
