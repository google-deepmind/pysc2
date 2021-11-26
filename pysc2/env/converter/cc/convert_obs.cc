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

#include "absl/container/flat_hash_map.h"
#include "absl/container/flat_hash_set.h"
#include "pysc2/env/converter/cc/castops.h"
#include "pysc2/env/converter/cc/game_data/uint8_lookup.h"
#include "pysc2/env/converter/cc/general_order_ids.h"
#include "pysc2/env/converter/cc/map_util.h"
#include "pysc2/env/converter/cc/raw_actions_encoder.h"
#include "pysc2/env/converter/cc/raw_camera.h"
#include "pysc2/env/converter/cc/tensor_util.h"
#include "s2clientprotocol/raw.pb.h"

namespace pysc2 {
namespace {

constexpr int kMaskedUnitTypeId = 254;

static std::array<int, 35> kUnitFeaturesToMask({
    // 1: alliance.
    2,  // health.
    3,  // shield.
    4,  // energy.
    5,  // cargo_space_taken.
    6,  // build_progress.
    7,  // health_ratio.
    8,  // shield_ratio.
    9,  // energy_ratio.
    // 10: display_type.
    // 11: owner.
    // 12: x.
    // 13: y.
    14,  // facing.
    // 15: radius.
    16,  // cloak.
    // 17: is_selected.
    // 18: is_blip.
    19,  // is_powered.
    20,  // mineral_contents.
    21,  // vespene_contents.
    22,  // carg_space_max.
    23,  // assigned_harvesters.
    24,  // ideal_harvesters.
    25,  // weapon_cooldown.
    26,  // order_length.
    27,  // order_id_0.
    28,  // order_id_1.
    // 29: tag (used for bookkeeping, not part of the observation).
    30,  // hallucination.
    31,  // buff_id_0.
    32,  // buff_id_1.
    33,  // addon_unit_type.
    34,  // active.
    // 35: is_on_screen.
    36,  // order_progress_0.
    37,  // order_progress_1.
    38,  // order_id_2.
    39,  // order_id_3.
    40,  // is_in_cargo.
    41,  // buff_duration_remain.
    42,  // buff_duration_max.
    43,  // attack_upgrade_level.
    44,  // armor_upgrade_level.
    45,  // shield_upgrade_level.
});

}  // namespace

dm_env_rpc::v1::Tensor GameLoop(
    const SC2APIProtocol::Observation& observation) {
  return MakeTensor(
      std::vector<int>({static_cast<int>(observation.game_loop())}));
}

dm_env_rpc::v1::Tensor PlayerCommon(const SC2APIProtocol::Observation& obs) {
  const SC2APIProtocol::PlayerCommon& player = obs.player_common();

  dm_env_rpc::v1::Tensor output = ZeroVector<int32_t>(kNumPlayerFeatures);
  MutableVector<int32_t> v(&output);
  v(0) = player.player_id();
  v(1) = player.minerals();
  v(2) = player.vespene();
  v(3) = player.food_used();
  v(4) = player.food_cap();
  v(5) = player.food_army();
  v(6) = player.food_workers();
  v(7) = player.idle_worker_count();
  v(8) = player.army_count();
  v(9) = player.warp_gate_count();
  v(10) = player.larva_count();

  return output;
}

dm_env_rpc::v1::Tensor MapPlayerIdToOne(const dm_env_rpc::v1::Tensor& player) {
  dm_env_rpc::v1::Tensor output = player;
  output.mutable_int32s()->set_array(0, 1);
  return output;
}

dm_env_rpc::v1::Tensor Upgrades(const SC2APIProtocol::Observation& obs) {
  const SC2APIProtocol::PlayerRaw& player = obs.raw_data().player();
  dm_env_rpc::v1::Tensor output =
      ZeroVector<int32_t>(player.upgrade_ids_size());
  MutableVector<int32_t> v(&output);
  for (int i = 0; i < player.upgrade_ids_size(); i++) {
    v(i) = player.upgrade_ids(i);
  }

  return output;
}

dm_env_rpc::v1::Tensor UpgradesUint8FixedLength(
    const dm_env_rpc::v1::Tensor& upgrades, int max_num_upgrades) {
  dm_env_rpc::v1::Tensor output = ZeroVector<int32_t>(max_num_upgrades);
  MutableVector<int32_t> v(&output);
  for (int i = 0; i < upgrades.shape(0) && i < max_num_upgrades; ++i) {
    v(i) = PySc2ToUint8Upgrades(upgrades.int32s().array(i));
  }

  return output;
}

dm_env_rpc::v1::TensorSpec RawUnitsSpec(int max_unit_count, int num_unit_types,
                                        int num_unit_features,
                                        int num_action_types) {
  dm_env_rpc::v1::TensorSpec spec;
  spec.set_name("raw_units");
  spec.set_dtype(dm_env_rpc::v1::DataType::INT32);
  spec.add_shape(max_unit_count);
  spec.add_shape(num_unit_features + 2);

  // All mins are 0, as that is what is populated when there is no unit.
  for (int j = 0; j < max_unit_count; ++j) {
    for (int i = 0; i < num_unit_features + 2; ++i) {
      spec.mutable_min()->mutable_int32s()->add_array(0);
    }
  }

  // We populate an array with all maxes, then broadcast that into the spec
  // taking the actual requested number of features into account.
  std::array<int, 46> max({
      kMaskedUnitTypeId,                // 0, unit type.
      SC2APIProtocol::Alliance_MAX,     // 1, alliance.
      10000,                            // 2, health.
      1000,                             // 3, shield.
      200,                              // 4, energy.
      8,                                // 5, cargo space.
      100,                              // 6, build progress.
      255,                              // 7, health ratio.
      255,                              // 8, shield ratio.
      255,                              // 9, energy ratio.
      SC2APIProtocol::DisplayType_MAX,  // 10, display type.
      16,                               // 11, owner.
      256,                              // 12, minimap pos x.
      256,                              // 13, minimap pos y.
      7,                                // 14, facing.
      13,                               // 15, minimap radius.
      SC2APIProtocol::CloakState_MAX,   // 16, cloak state.
      1,                                // 17, is selected.
      1,                                // 18, is blip.
      1,                                // 19, is powered.
      1800,                             // 20, mineral contents.
      2250,                             // 21, vespene contents.
      8,                                // 22, cargo space max.
      64,                               // 23, assigned harvesters.
      64,                               // 24, ideal harvesters.
      50,                               // 25, weapon cooldown.
      32,                               // 26, orders size.
      num_action_types - 1,             // 27, order 0.
      num_action_types - 1,             // 28, order 1.
      INT_MAX,                          // 29, unit tag.
      1,                                // 30, is hallucination.
      MaximumBuffId(),                  // 31, buff 0.
      MaximumBuffId(),                  // 32, buff 1.
      42,                               // 33, add-on unit tag. Needs -> uint8.
      1,                                // 34, is active.
      1,                                // 35, is on screen.
      100,                              // 36, order 0 progress.
      100,                              // 37, order 1 progress.
      num_action_types - 1,             // 38, order 2.
      num_action_types - 1,             // 39, order 3.
      1,                                // 40, in cargo.
      4000,                             // 41, buff duration remain.
      4000,                             // 42, buff duration max.
      3,                                // 43, attack upgrade level.
      3,                                // 44, armor upgrade level.
      3,                                // 45, shield upgrade level.
  });

  for (int j = 0; j < max_unit_count; ++j) {
    for (int i = 0; i < num_unit_features; ++i) {
      spec.mutable_max()->mutable_int32s()->add_array(max[i]);
    }
    // The extra 2 features.
    spec.mutable_max()->mutable_int32s()->add_array(1);  // unit selected.
    spec.mutable_max()->mutable_int32s()->add_array(1);  // unit targetted.
  }
  return spec;
}

dm_env_rpc::v1::Tensor RawUnitsFullVec(
    const absl::flat_hash_set<int64_t>& last_unit_tags,
    const int64_t last_target_unit_tag,
    const SC2APIProtocol::ObservationRaw& raw, int max_unit_count, bool is_raw,
    const SC2APIProtocol::Size2DI& map_size,
    const SC2APIProtocol::Size2DI& raw_resolution, int num_unit_types,
    int num_unit_features, bool mask_offscreen_enemies, int num_action_types,
    bool add_effects_to_units, bool add_cargo_to_units, RawCamera* camera) {
  dm_env_rpc::v1::Tensor output =
      ZeroMatrix<int32_t>(max_unit_count, num_unit_features + 2);
  MutableMatrix<int32_t> m(&output);

  absl::flat_hash_map<uint64_t, uint32_t> tag_types;
  for (const SC2APIProtocol::Unit& u : raw.units()) {
    tag_types[u.tag()] = u.unit_type();
  }

  int i = 0;
  int unit_count = std::min(max_unit_count, raw.units_size());
  for (; i < unit_count; i++) {
    const SC2APIProtocol::Unit& u = raw.units(i);

    SC2APIProtocol::PointI minimap =
        WorldToMinimapPx(u.pos(), map_size, raw_resolution);
    int minimap_pos_x = minimap.x();
    int minimap_pos_y = minimap.y();
    int minimap_radius =
        WorldToMinimapDistance(u.radius(), map_size, raw_resolution);

    // Match unit_vec order
    m(i, 0) = u.unit_type();
    m(i, 1) = u.alliance();  // Self = 1, Ally = 2, Neutral = 3, Enemy = 4
    m(i, 2) = ToInt32(u.health());
    m(i, 3) = ToInt32(u.shield());
    m(i, 4) = ToInt32(u.energy());
    m(i, 5) = u.cargo_space_taken();
    m(i, 6) = ToInt32(static_cast<double>(u.build_progress()) * 100.0);

    // Resume API order
    if (u.health_max() > 0) {
      m(i, 7) = ToInt32(u.health() / u.health_max() * 255.0);
    } else {
      m(i, 7) = 0;
    }
    if (u.shield_max() > 0) {
      m(i, 8) = ToInt32(u.shield() / u.shield_max() * 255.0);
    } else {
      m(i, 8) = 0;
    }
    if (u.energy_max() > 0) {
      m(i, 9) = ToInt32(u.energy() / u.energy_max() * 255.0);
    } else {
      m(i, 9) = 0;
    }
    m(i, 10) = u.display_type();  // Visible = 1; Snapshot = 2; Hidden = 3
    m(i, 11) = u.owner();         //  1 - 15;    16 = neutral
    m(i, 12) = minimap_pos_x;
    m(i, 13) = minimap_pos_y;
    m(i, 14) = ToInt32(u.facing());
    m(i, 15) = minimap_radius;
    m(i, 16) = u.cloak();  // Cloaked = 1; CloakedDetected = 2; NotCloaked = 3
    m(i, 17) = u.is_selected();
    m(i, 18) = u.is_blip();
    m(i, 19) = u.is_powered();
    m(i, 20) = u.mineral_contents();
    m(i, 21) = u.vespene_contents();

    // Not populated for enemies or neutral
    m(i, 22) = u.cargo_space_max();
    m(i, 23) = u.assigned_harvesters();
    m(i, 24) = u.ideal_harvesters();
    m(i, 25) = ToInt32(u.weapon_cooldown());
    m(i, 26) = u.orders_size();
    if (u.orders_size() > 0) {
      m(i, 27) = GeneralOrderId(RawAbilityToGameId(u.orders(0).ability_id()),
                                num_action_types);
    } else {
      m(i, 27) = 0;
    }
    if (u.orders_size() > 1) {
      m(i, 28) = GeneralOrderId(RawAbilityToGameId(u.orders(1).ability_id()),
                                num_action_types);
    } else {
      m(i, 28) = 0;
    }
    if (is_raw) {
      m(i, 29) = u.tag();
    } else {
      m(i, 29) = 0;
    }

    if (num_unit_features > 33) {
      m(i, 30) = u.is_hallucination();
      if (u.buff_ids_size() >= 1) {
        m(i, 31) = u.buff_ids(0);
      } else {
        m(i, 31) = 0;
      }
      if (u.buff_ids_size() >= 2) {
        m(i, 32) = u.buff_ids(1);
      } else {
        m(i, 32) = 0;
      }
      if (u.has_add_on_tag()) {
        const auto it = tag_types.find(u.add_on_tag());
        if (it != tag_types.end()) {
          m(i, 33) = it->second;
        } else {
          m(i, 33) = 0;
        }
      } else {
        m(i, 33) = 0;
      }
    }

    if (num_unit_features > 34) {
      m(i, 34) = u.is_active();
    }

    bool is_on_screen = false;
    if (camera) {
      is_on_screen = camera->IsOnScreen(u.pos().x(), u.pos().y());
    } else {
      is_on_screen = u.is_on_screen();
    }

    if (num_unit_features > 35) {
      m(i, 35) = is_on_screen;
    }

    if (num_unit_features > 39) {
      if (u.orders_size() >= 1) {
        m(i, 36) = ToInt32(static_cast<double>(u.orders(0).progress()) * 100.0);
      }
      if (u.orders_size() >= 2) {
        m(i, 37) = ToInt32(static_cast<double>(u.orders(1).progress()) * 100.0);
      }
      if (u.orders_size() > 2) {
        m(i, 38) = GeneralOrderId(RawAbilityToGameId(u.orders(2).ability_id()),
                                  num_action_types);
      } else {
        m(i, 38) = 0;
      }
      if (u.orders_size() > 3) {
        m(i, 39) = GeneralOrderId(RawAbilityToGameId(u.orders(3).ability_id()),
                                  num_action_types);
      } else {
        m(i, 39) = 0;
      }
    }

    if (num_unit_features > 45) {
      m(i, 41) = u.buff_duration_remain();
      m(i, 42) = u.buff_duration_max();
      m(i, 43) = u.attack_upgrade_level();
      m(i, 44) = u.armor_upgrade_level();
      m(i, 45) = u.shield_upgrade_level();
    }

    if (last_unit_tags.find(u.tag()) != last_unit_tags.end()) {
      m(i, num_unit_features) = 1;
    } else {
      m(i, num_unit_features) = 0;
    }
    if (last_target_unit_tag == u.tag()) {
      m(i, num_unit_features + 1) = 1;
    } else {
      m(i, num_unit_features + 1) = 0;
    }

    bool mask_enemy = mask_offscreen_enemies &&
                      u.alliance() == SC2APIProtocol::Enemy && !is_on_screen;
    if (mask_enemy && u.cloak() == SC2APIProtocol::Cloaked) {
      for (int j = 0; j < num_unit_features + 2; j++) {
        m(i, j) = 0;
      }
      if (is_raw) {
        // Unit tag should not be used directly by the agent, but is used for
        // various things like masking.
        m(i, 29) = u.tag();
      }
    }

    if (mask_enemy && u.display_type() == SC2APIProtocol::Visible) {
      // Mask out features that should not be visible by camera agents outside
      // of the camera.
      m(i, 0) = kMaskedUnitTypeId;  // unit_type.

      for (auto f : kUnitFeaturesToMask) {
        if (f < num_unit_features + 2) {
          m(i, f) = 0;
        }
      }

      CHECK_LE(num_unit_features, 46)
          << "You need to update the list of masked unit features.";
    }
  }

  if (add_cargo_to_units) {
    // Add cargo at the end, treat them as units for now.
    for (const SC2APIProtocol::Unit& u : raw.units()) {
      SC2APIProtocol::PointI minimap_pos =
          WorldToMinimapPx(u.pos(), map_size, raw_resolution);
      int minimap_pos_x = minimap_pos.x();
      int minimap_pos_y = minimap_pos.y();

      for (const SC2APIProtocol::PassengerUnit& p : u.passengers()) {
        if (i >= max_unit_count) {
          break;
        }

        m(i, 0) = p.unit_type();
        m(i, 1) = u.alliance();
        m(i, 2) = ToInt32(p.health());
        m(i, 3) = ToInt32(p.shield());
        m(i, 4) = ToInt32(p.energy());
        if (p.health_max() > 0) {
          m(i, 7) = ToInt32(p.health() / p.health_max() * 255.0);
        } else {
          m(i, 7) = 0;
        }
        if (p.shield_max() > 0) {
          m(i, 8) = ToInt32(p.shield() / p.shield_max() * 255.0);
        } else {
          m(i, 8) = 0;
        }
        if (p.energy_max() > 0) {
          m(i, 9) = ToInt32(p.energy() / p.energy_max() * 255.0);
        } else {
          m(i, 9) = 0;
        }
        m(i, 11) = u.owner();
        m(i, 12) = minimap_pos_x;
        m(i, 13) = minimap_pos_y;
        if (is_raw) {
          m(i, 29) = p.tag();
        }
        if (40 < num_unit_features + 2) {
          m(i, 40) = 1;  // In cargo
        }

        i++;
      }
    }
  }

  if (add_effects_to_units) {
    // Add effects at the end, treat them as units for now.
    for (const SC2APIProtocol::Effect& e : raw.effects()) {
      if (i >= max_unit_count) {
        break;
      }
      for (const SC2APIProtocol::Point2D& pos : e.pos()) {
        if (i >= max_unit_count) {
          break;
        }

        SC2APIProtocol::PointI minimap_pos =
            WorldToMinimapPx(pos, map_size, raw_resolution);
        int minimap_pos_x = minimap_pos.x();
        int minimap_pos_y = minimap_pos.y();

        // int minimap_radius =
        //     WorldToMinimapDistance(e.radius(), map_size, raw_resolution);

        m(i, 0) = e.effect_id() + num_unit_types;
        m(i, 1) = e.alliance();
        m(i, 11) = e.owner();
        m(i, 12) = minimap_pos_x;
        m(i, 13) = minimap_pos_y;
        // TODO(petkoig): Transform radius when sc2_env changes.
        m(i, 15) = ToInt32(e.radius());

        i++;
      }
    }
  }

  return output;
}

dm_env_rpc::v1::Tensor RawUnitsToUint8(const dm_env_rpc::v1::Tensor& tensor,
                                       int num_unit_features) {
  dm_env_rpc::v1::Tensor output = tensor;
  MutableMatrix<int32_t> o(&output);

  for (int i = 0; i < o.height(); i++) {
    if ((o(i, 10) > 0 && o(i, 0) != kMaskedUnitTypeId) ||
        ((num_unit_features > 40) && o(i, 40) == 1)) {
      // This is a unit type as it has a display type or is in cargo.
      // We do not convert effect ids or uncheat unit types.
      o(i, 0) = PySc2ToUint8(o(i, 0));
    }
    if (num_unit_features > 32) {
      // Buffs are added in unit features observation.
      o(i, 31) = PySc2ToUint8Buffs(o(i, 31));
      o(i, 32) = PySc2ToUint8Buffs(o(i, 32));
    }
  }
  return output;
}

dm_env_rpc::v1::Tensor CameraPosition(
    const SC2APIProtocol::Observation& obs,
    const SC2APIProtocol::Size2DI& map_size,
    const SC2APIProtocol::Size2DI& raw_resolution, RawCamera* camera) {
  SC2APIProtocol::Point2D xy;
  if (camera) {
    xy.set_x(camera->X());
    xy.set_y(camera->Y());
  } else {
    const SC2APIProtocol::Point& cam = obs.raw_data().player().camera();
    xy.set_x(cam.x());
    xy.set_y(cam.y());
  }
  SC2APIProtocol::PointI transformed =
      WorldToMinimapPx(xy, map_size, raw_resolution);

  dm_env_rpc::v1::Tensor output;
  output.add_shape(2);
  output.mutable_int32s()->add_array(transformed.x());
  output.mutable_int32s()->add_array(transformed.y());
  return output;
}

dm_env_rpc::v1::Tensor CameraSize(const SC2APIProtocol::Size2DI& raw_resolution,
                                  const SC2APIProtocol::Size2DI& map_size,
                                  int camera_width_world_units) {
  float scale = static_cast<float>(camera_width_world_units) /
                std::max(map_size.x(), map_size.y());
  float x = static_cast<float>(raw_resolution.x()) * scale;
  float y = static_cast<float>(raw_resolution.y()) * scale;

  dm_env_rpc::v1::Tensor output;
  output.add_shape(2);
  output.mutable_int32s()->add_array(x);
  output.mutable_int32s()->add_array(y);
  return output;
}

dm_env_rpc::v1::Tensor SeparateCamera(
    const dm_env_rpc::v1::Tensor& camera_position,
    const dm_env_rpc::v1::Tensor& camera_size,
    const SC2APIProtocol::Size2DI& raw_resolution) {
  dm_env_rpc::v1::Tensor output;
  output.add_shape(raw_resolution.y());
  output.add_shape(raw_resolution.x());

  const auto size = raw_resolution.y() * raw_resolution.x();
  for (int i = 0; i < size; ++i) {
    output.mutable_int32s()->add_array(0);
  }

  auto px = camera_position.int32s().array(0);
  auto py = camera_position.int32s().array(1);
  auto sx = camera_size.int32s().array(0);
  auto sy = camera_size.int32s().array(1);
  int y_lower = std::max(py - (sy / 2), 0);
  int y_upper = std::min(py + (sy / 2), raw_resolution.y());
  int x_lower = std::max(px - (sx / 2), 0);
  int x_upper = std::min(px + (sx / 2), raw_resolution.x());

  for (int j = y_lower; j < y_upper; j++) {
    for (int i = x_lower; i < x_upper; i++) {
      output.mutable_int32s()->set_array(j * raw_resolution.x() + i, 1);
    }
  }

  return output;
}

int GetUnitTypeIndex(int unit_type_id, bool using_uint8_unit_ids) {
  if (using_uint8_unit_ids) {
    return unit_type_id - 1;
  } else {
    return PySc2ToUint8(unit_type_id) - 1;
  }
}

dm_env_rpc::v1::Tensor UnitCounts(const SC2APIProtocol::Observation& obs,
                                  bool include_hallucinations,
                                  bool only_count_finished_units) {
  // Count the units.
  // TODO(petkoig): Check maximum size of unit types and use vector instead.
  absl::flat_hash_map<int64_t, int64_t> unit_counts;
  const SC2APIProtocol::ObservationRaw& raw = obs.raw_data();
  for (int i = 0; i < raw.units_size(); i++) {
    const SC2APIProtocol::Unit& unit = raw.units(i);
    if (unit.alliance() == SC2APIProtocol::Self &&
        (include_hallucinations || !unit.is_hallucination()) &&
        (!only_count_finished_units || unit.build_progress() == 1.0)) {
      unit_counts[unit.unit_type()]++;
    }
  }

  // Sort them by count in ascending order.
  std::vector<std::pair<int64_t, int64_t>> unit_count_items(unit_counts.begin(),
                                                            unit_counts.end());
  std::sort(
      unit_count_items.begin(), unit_count_items.end(),
      [](const std::pair<int64_t, int64_t>& a,
         const std::pair<int64_t, int64_t>& b) { return a.second < b.second; });

  dm_env_rpc::v1::Tensor output =
      ZeroMatrix<int64_t>(unit_count_items.size(), 2);
  MutableMatrix<int64_t> m(&output);
  for (size_t i = 0; i < unit_count_items.size(); i++) {
    m(i, 0) = unit_count_items[i].first;
    m(i, 1) = unit_count_items[i].second;
  }

  return output;
}

dm_env_rpc::v1::Tensor AddUnitCountsBowData(
    const dm_env_rpc::v1::Tensor& unit_counts, int num_unit_types,
    bool using_uint8_unit_ids) {
  dm_env_rpc::v1::Tensor output = ZeroVector<int32_t>(num_unit_types);
  MutableVector<int32_t> v(&output);
  Matrix<int64_t> m(unit_counts);
  for (int i = 0; i < m.height(); ++i) {
    int index = GetUnitTypeIndex(m(i, 0), using_uint8_unit_ids);
    if (index >= 0 && index < num_unit_types) {
      v(index) = m(i, 1);
    }
  }

  return output;
}

}  // namespace pysc2
