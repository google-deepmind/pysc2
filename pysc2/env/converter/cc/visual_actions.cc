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

#include <algorithm>
#include <functional>
#include <utility>

#include "glog/logging.h"
#include "absl/strings/str_cat.h"
#include "absl/strings/string_view.h"
#include "pysc2/env/converter/cc/game_data/visual_actions.h"
#include "pysc2/env/converter/cc/tensor_util.h"
#include "s2clientprotocol/common.pb.h"
#include "s2clientprotocol/spatial.pb.h"
#include "s2clientprotocol/ui.pb.h"

namespace pysc2 {
namespace {

bool ActionComparator(const VisualAction& lhs, const VisualAction& rhs) {
  return lhs.action_id() < rhs.action_id();
}

class VisualActions {
 public:
  explicit VisualActions(const std::vector<Function>& functions) {
    actions_.reserve(functions.size());
    for (const Function& f : functions) {
      actions_.emplace_back(f.action_id, f.label, f.type, f.ability_id,
                            f.general_id);
    }

    std::sort(actions_.begin(), actions_.end(), ActionComparator);
    for (int i = 0; i < actions_.size(); ++i) {
      CHECK_EQ(actions_[i].action_id(), i) << "Non-contiguous actions @ " << i;
    }

    for (const VisualAction& action : actions_) {
      AbilityId ability_id = action.ability_id();
      auto iter = ability_id_to_actions_.find(ability_id);
      if (iter != ability_id_to_actions_.end()) {
        iter->second.push_back(action);
      } else {
        ability_id_to_actions_.insert(
            {ability_id, std::vector<VisualAction>({action})});
      }
    }
  }

  const VisualAction& GetAction(int action_id) const {
    return actions_[action_id];
  }

  const std::vector<VisualAction>& GetAbilityActions(
      AbilityId ability_id) const {
    auto iter = ability_id_to_actions_.find(ability_id);
    CHECK(iter != ability_id_to_actions_.end());
    return iter->second;
  }

  bool HasAbility(AbilityId ability_id) const {
    return ability_id_to_actions_.find(ability_id) !=
           ability_id_to_actions_.end();
  }

 private:
  std::vector<VisualAction> actions_;
  absl::flat_hash_map<AbilityId, std::vector<VisualAction>>
      ability_id_to_actions_;
};

const VisualActions& GetActions() {
  static const VisualActions* kActions = new VisualActions(VisualFunctions());

  return *kActions;
}  // NOLINT(readability/fn_size)

int Val(const dm_env_rpc::v1::Tensor& tensor) { return ToScalar(tensor); }

int Option(const dm_env_rpc::v1::Tensor& arg) {
  // In proto these are 1-based, in python 0-based (with a lookup which maps
  // them back to 1-based). Hence in C++ we need to add 1.
  return Val(arg) + 1;
}

SC2APIProtocol::PointI MakePoint(int arg, int width) {
  SC2APIProtocol::PointI point;
  point.set_x(arg % width);
  point.set_y(arg / width);
  return point;
}

int PointTo1D(const SC2APIProtocol::PointI& point, int width) {
  return point.y() * width + point.x();
}

const dm_env_rpc::v1::Tensor& Arg(
    absl::string_view name,
    const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& arguments,
    absl::string_view context) {
  auto arg = arguments.find(name);
  CHECK(arg != arguments.cend())
      << name << " is required for the " << context << " action";
  return arg->second;
}

SC2APIProtocol::Action MoveCamera(
    const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& arguments,
    const ActionContext& action_context, AbilityId ability_id) {
  absl::string_view ctx = "move camera";
  SC2APIProtocol::Action action;
  *action.mutable_action_feature_layer()
       ->mutable_camera_move()
       ->mutable_center_minimap() = MakePoint(
      Val(Arg("minimap", arguments, ctx)), action_context.minimap_width);

  return action;
}

SC2APIProtocol::Action SelectPoint(
    const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& arguments,
    const ActionContext& action_context, AbilityId ability_id) {
  absl::string_view ctx = "select_point";
  SC2APIProtocol::Action action;
  SC2APIProtocol::ActionSpatialUnitSelectionPoint* unit_selection_point =
      action.mutable_action_feature_layer()->mutable_unit_selection_point();

  unit_selection_point->set_type(
      SC2APIProtocol::ActionSpatialUnitSelectionPoint::Type(
          Option(Arg("select_point_act", arguments, ctx))));
  *unit_selection_point->mutable_selection_screen_coord() = MakePoint(
      Val(Arg("screen", arguments, ctx)), action_context.screen_width);
  return action;
}

SC2APIProtocol::Action SelectRect(
    const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& arguments,
    const ActionContext& action_context, AbilityId ability_id) {
  absl::string_view ctx = "select rect";
  SC2APIProtocol::Action action;
  SC2APIProtocol::ActionSpatialUnitSelectionRect* unit_selection_rect =
      action.mutable_action_feature_layer()->mutable_unit_selection_rect();
  SC2APIProtocol::RectangleI* rect =
      unit_selection_rect->add_selection_screen_coord();

  unit_selection_rect->set_selection_add(
      static_cast<bool>(Val(Arg("select_add", arguments, ctx))));
  auto s = MakePoint(Val(Arg("screen", arguments, ctx)),
                     action_context.screen_width);
  auto s2 = MakePoint(Val(Arg("screen2", arguments, ctx)),
                      action_context.screen_width);
  rect->mutable_p0()->set_x(std::min(s.x(), s2.x()));
  rect->mutable_p0()->set_y(std::min(s.y(), s2.y()));
  rect->mutable_p1()->set_x(std::max(s.x(), s2.x()));
  rect->mutable_p1()->set_y(std::max(s.y(), s2.y()));
  return action;
}

SC2APIProtocol::Action SelectIdleWorker(
    const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& arguments,
    const ActionContext& action_context, AbilityId ability_id) {
  absl::string_view ctx = "select idle worker";
  SC2APIProtocol::Action action;
  action.mutable_action_ui()->mutable_select_idle_worker()->set_type(
      SC2APIProtocol::ActionSelectIdleWorker::Type(
          Option(Arg("select_worker", arguments, ctx))));
  return action;
}

SC2APIProtocol::Action SelectArmy(
    const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& arguments,
    const ActionContext& action_context, AbilityId ability_id) {
  absl::string_view ctx = "select army";
  SC2APIProtocol::Action action;
  action.mutable_action_ui()->mutable_select_army()->set_selection_add(
      static_cast<bool>(Val(Arg("select_add", arguments, ctx))));
  return action;
}

SC2APIProtocol::Action SelectWarpGates(
    const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& arguments,
    const ActionContext& action_context, AbilityId ability_id) {
  absl::string_view ctx = "select warp gates";
  SC2APIProtocol::Action action;
  action.mutable_action_ui()->mutable_select_warp_gates()->set_selection_add(
      static_cast<bool>(Val(Arg("select_add", arguments, ctx))));
  return action;
}

SC2APIProtocol::Action SelectLarva(
    const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& arguments,
    const ActionContext& action_context, AbilityId ability_id) {
  SC2APIProtocol::Action action;
  *action.mutable_action_ui()->mutable_select_larva() =
      SC2APIProtocol::ActionSelectLarva();
  return action;
}

SC2APIProtocol::Action SelectUnit(
    const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& arguments,
    const ActionContext& action_context, AbilityId ability_id) {
  absl::string_view ctx = "select unit";
  SC2APIProtocol::Action action;
  SC2APIProtocol::ActionMultiPanel* multi_panel =
      action.mutable_action_ui()->mutable_multi_panel();

  multi_panel->set_type(SC2APIProtocol::ActionMultiPanel::Type(
      Option(Arg("select_unit_act", arguments, ctx))));
  multi_panel->set_unit_index(Val(Arg("select_unit_id", arguments, ctx)));
  return action;
}

SC2APIProtocol::Action SelectControlGroup(
    const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& arguments,
    const ActionContext& action_context, AbilityId ability_id) {
  absl::string_view ctx = "select control group";
  SC2APIProtocol::Action action;
  SC2APIProtocol::ActionControlGroup* control_group =
      action.mutable_action_ui()->mutable_control_group();

  control_group->set_action(
      SC2APIProtocol::ActionControlGroup::ControlGroupAction(
          Option(Arg("control_group_act", arguments, ctx))));
  control_group->set_control_group_index(
      Val(Arg("control_group_id", arguments, ctx)));
  return action;
}

SC2APIProtocol::Action Unload(
    const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& arguments,
    const ActionContext& action_context, AbilityId ability_id) {
  absl::string_view ctx = "unload";
  SC2APIProtocol::Action action;
  action.mutable_action_ui()->mutable_cargo_panel()->set_unit_index(
      Val(Arg("unload_id", arguments, ctx)));
  return action;
}

SC2APIProtocol::Action BuildQueue(
    const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& arguments,
    const ActionContext& action_context, AbilityId ability_id) {
  absl::string_view ctx = "build queue";
  SC2APIProtocol::Action action;
  action.mutable_action_ui()->mutable_production_panel()->set_unit_index(
      Val(Arg("build_queue_id", arguments, ctx)));
  return action;
}

SC2APIProtocol::Action CmdQuick(
    const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& arguments,
    const ActionContext& action_context, AbilityId ability_id) {
  absl::string_view ctx = "cmd quick";
  SC2APIProtocol::Action action;
  SC2APIProtocol::ActionSpatialUnitCommand* command =
      action.mutable_action_feature_layer()->mutable_unit_command();
  command->set_queue_command(
      static_cast<bool>(Val(Arg("queued", arguments, ctx))));
  command->set_ability_id(ability_id);
  return action;
}

SC2APIProtocol::Action CmdScreen(
    const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& arguments,
    const ActionContext& action_context, AbilityId ability_id) {
  absl::string_view ctx = "cmd screen";
  SC2APIProtocol::Action action;
  SC2APIProtocol::ActionSpatialUnitCommand* command =
      action.mutable_action_feature_layer()->mutable_unit_command();
  command->set_queue_command(
      static_cast<bool>(Val(Arg("queued", arguments, ctx))));
  command->set_ability_id(ability_id);
  *command->mutable_target_screen_coord() = MakePoint(
      Val(Arg("screen", arguments, ctx)), action_context.screen_width);
  return action;
}

SC2APIProtocol::Action CmdMinimap(
    const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& arguments,
    const ActionContext& action_context, AbilityId ability_id) {
  absl::string_view ctx = "cmd minimap";
  SC2APIProtocol::Action action;
  SC2APIProtocol::ActionSpatialUnitCommand* command =
      action.mutable_action_feature_layer()->mutable_unit_command();
  command->set_queue_command(
      static_cast<bool>(Val(Arg("queued", arguments, ctx))));
  command->set_ability_id(ability_id);
  *command->mutable_target_minimap_coord() = MakePoint(
      Val(Arg("minimap", arguments, ctx)), action_context.minimap_width);
  return action;
}

SC2APIProtocol::Action Autocast(
    const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& arguments,
    const ActionContext& action_context, AbilityId ability_id) {
  SC2APIProtocol::Action action;
  action.mutable_action_ui()->mutable_toggle_autocast()->set_ability_id(
      ability_id);
  return action;
}

absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> MakeFunctionCall(
    ActionId action_id, const absl::flat_hash_map<std::string, int>& args) {
  absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> fn_call;
  fn_call["function"] = MakeTensor(action_id);
  for (const auto& [k, v] : args) {
    fn_call[k] = MakeTensor(v);
  }

  return fn_call;
}

absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> NoOp() {
  return MakeFunctionCall(no_op, absl::flat_hash_map<std::string, int>({}));
}

absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> Ability(
    AbilityId ability_id, FunctionType action_type, bool queue = false,
    int coord = 0) {
  if (!GetActions().HasAbility(ability_id)) {
    LOG(WARNING) << "Unknown ability_id:" << ability_id
                 << "This is probably dance or cheer, or some unknown new "
                 << "or map specific ability. Treating it as a no-op.";
    return NoOp();
  }

  auto actions = GetActionsForAbility(ability_id);
  int general_id;
  if (actions[0].general_id() != 0) {
    general_id = actions[0].general_id();
  } else {
    general_id = ability_id;
  }

  const auto& general_actions = GetActionsForAbility(general_id);
  for (const auto& general_action : general_actions) {
    if (general_action.action_type() == action_type) {
      switch (action_type) {
        case cmd_screen:
          return MakeFunctionCall(general_action.action_id(),
                                  {{"queued", queue}, {"screen", coord}});
        case cmd_minimap:
          return MakeFunctionCall(general_action.action_id(),
                                  {{"queued", queue}, {"minimap", coord}});
        case cmd_quick:
          return MakeFunctionCall(general_action.action_id(),
                                  {{"queued", queue}});
        case autocast:
          return MakeFunctionCall(general_action.action_id(), {});
        default:
          LOG(FATAL) << "Unhandled ability action type " << action_type;
      }
    }
  }

  LOG(ERROR) << "Unable to decode ability id " << ability_id
             << ", type: " << action_type << ". Likely a bug.";
  return NoOp();
}
}  // namespace

VisualAction::VisualAction(ActionId action_id, absl::string_view tag,
                           FunctionType action_type, AbilityId ability_id,
                           GeneralId general_id)
    : tag_(tag),
      action_type_(action_type),
      action_id_(action_id),
      ability_id_(ability_id),
      general_id_(general_id) {}

bool VisualAction::IsApplicable(bool requires_point) const {
  if (requires_point) {
    switch (action_type_) {
      case cmd_screen:
      case cmd_minimap:
      case autocast:
        return true;
      default:
        return false;
    }
  } else {
    switch (action_type_) {
      case autocast:
      case cmd_quick:
        return true;
      default:
        return false;
    }
  }
}

SC2APIProtocol::Action VisualAction::Encode(
    const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& args,
    const ActionContext& action_context) const {
  CHECK_NE(action_type_, no_op) << "Don't call Encode() for no_op";

  static const auto* fn_map = new absl::flat_hash_map<
      FunctionType,
      std::function<SC2APIProtocol::Action(
          const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>&,
          const ActionContext&, AbilityId)>>(
      {{move_camera, MoveCamera},
       {select_point, SelectPoint},
       {select_rect, SelectRect},
       {select_control_group, SelectControlGroup},
       {select_unit, SelectUnit},
       {select_idle_worker, SelectIdleWorker},
       {select_army, SelectArmy},
       {select_warp_gates, SelectWarpGates},
       {select_larva, SelectLarva},
       {unload, Unload},
       {build_queue, BuildQueue},
       {cmd_screen, CmdScreen},
       {cmd_minimap, CmdMinimap},
       {cmd_quick, CmdQuick},
       {autocast, Autocast}});

  return fn_map->find(action_type_)->second(args, action_context, ability_id_);
}

const VisualAction& GetAction(ActionId action_id) {
  return GetActions().GetAction(action_id);
}

const std::vector<VisualAction>& GetActionsForAbility(AbilityId ability_id) {
  return GetActions().GetAbilityActions(ability_id);
}

absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> Decode(
    const SC2APIProtocol::RequestAction& request_action,
    const ActionContext& action_context) {
  for (const SC2APIProtocol::Action& action : request_action.actions()) {
    if (action.has_action_ui() || action.has_action_feature_layer()) {
      VLOG(1) << "Found action:\n" << action;
      if (action.has_action_ui()) {
        const auto& act_ui = action.action_ui();
        if (act_ui.has_multi_panel()) {
          return MakeFunctionCall(
              select_unit,
              {{"select_unit_act", act_ui.multi_panel().type() - 1},
               {"select_unit_id", act_ui.multi_panel().unit_index()}});
        } else if (act_ui.has_control_group()) {
          return MakeFunctionCall(
              select_control_group,
              {{"control_group_act", act_ui.control_group().action() - 1},
               {"control_group_id",
                act_ui.control_group().control_group_index()}});
        } else if (act_ui.has_select_idle_worker()) {
          return MakeFunctionCall(
              select_idle_worker,
              {{"select_worker", act_ui.select_idle_worker().type() - 1}});
        } else if (act_ui.has_select_army()) {
          return MakeFunctionCall(
              select_army,
              {{"select_add", act_ui.select_army().selection_add()}});
        } else if (act_ui.has_select_warp_gates()) {
          return MakeFunctionCall(
              select_warp_gates,
              {{"select_add", act_ui.select_warp_gates().selection_add()}});
        } else if (act_ui.has_select_larva()) {
          return MakeFunctionCall(select_larva, {});
        } else if (act_ui.has_cargo_panel()) {
          return MakeFunctionCall(
              unload, {{"unload_id", act_ui.cargo_panel().unit_index()}});
        } else if (act_ui.has_production_panel()) {
          return MakeFunctionCall(
              build_queue,
              {{"build_queue_id", act_ui.production_panel().unit_index()}});
        } else if (act_ui.has_toggle_autocast()) {
          return Ability(act_ui.toggle_autocast().ability_id(), autocast);
        }
      } else if (action.has_action_feature_layer()) {
        const auto& act_sp = action.action_feature_layer();
        if (act_sp.has_camera_move()) {
          return MakeFunctionCall(
              move_camera,
              {{"minimap", PointTo1D(act_sp.camera_move().center_minimap(),
                                     action_context.minimap_width)}});
        } else if (act_sp.has_unit_selection_point()) {
          return MakeFunctionCall(
              select_point,
              {{"screen",
                PointTo1D(
                    act_sp.unit_selection_point().selection_screen_coord(),
                    action_context.screen_width)},
               {"select_point_act", act_sp.unit_selection_point().type() - 1}});
        } else if (act_sp.has_unit_selection_rect()) {
          return MakeFunctionCall(
              select_rect,
              {{"screen",
                PointTo1D(
                    act_sp.unit_selection_rect().selection_screen_coord(0).p0(),
                    action_context.screen_width)},
               {"screen2",
                PointTo1D(
                    act_sp.unit_selection_rect().selection_screen_coord(0).p1(),
                    action_context.screen_width)}});
        } else if (act_sp.has_unit_command()) {
          const auto& cmd = act_sp.unit_command();
          const bool queue = cmd.queue_command();
          absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor> output;
          if (cmd.has_target_screen_coord()) {
            output = Ability(cmd.ability_id(), cmd_screen, queue,
                             PointTo1D(cmd.target_screen_coord(),
                                       action_context.screen_width));
          } else if (cmd.has_target_minimap_coord()) {
            output = Ability(cmd.ability_id(), cmd_minimap, queue,
                             PointTo1D(cmd.target_minimap_coord(),
                                       action_context.minimap_width));
          } else {
            output = Ability(cmd.ability_id(), cmd_quick, queue);
          }
          // Reject this unit command if it is beyond num_functions.
          if (ToScalar(output["function"]) >= action_context.num_functions) {
            continue;
          } else {
            return output;
          }
        }
      } else {
        LOG(FATAL) << "Shouldn't get here";
      }
    }
  }

  // No relevant actions found. Return no-op.
  return NoOp();
}

}  // namespace pysc2
