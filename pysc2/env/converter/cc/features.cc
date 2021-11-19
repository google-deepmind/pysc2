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

#include "pysc2/env/converter/cc/features.h"

#include <algorithm>
#include <string>
#include <vector>

#include "absl/container/flat_hash_map.h"
#include "absl/status/status.h"
#include "absl/status/statusor.h"
#include "absl/strings/str_cat.h"
#include "pysc2/env/converter/cc/game_data/uint8_lookup.h"

namespace pysc2 {

static const auto* kScreenFeaturesScale =
    new absl::flat_hash_map<std::string, int>({
        {"height_map", 256},
        {"visibility_map", 4},
        {"creep", 2},
        {"power", 2},
        {"player_id", 17},
        {"player_relative", 5},
        {"unit_type", MaximumUnitTypeId() + 1},
        {"selected", 2},
        {"unit_hit_points_ratio", 256},
        {"unit_energy_ratio", 256},
        {"unit_shields_ratio", 256},
        {"unit_density", 16},
        {"unit_density_aa", 256},
        {"effects", 16},
        {"hallucinations", 2},
        {"cloaked", 2},
        {"blip", 2},
        {"active", 2},
        {"buffs", MaximumBuffId() + 1},
        {"buff_duration", 256},
        {"build_progress", 256},
        {"pathable", 2},
        {"buildable", 2},
    });

static const auto* kMinimapFeaturesScale =
    new absl::flat_hash_map<std::string, int>({
        {"height_map", 256},
        {"visibility_map", 4},
        {"creep", 2},
        {"camera", 2},
        {"player_id", 17},
        {"player_relative", 5},
        {"selected", 2},
        {"alerts", 2},
        {"pathable", 2},
        {"buildable", 2},                        // Cheating.
        {"unit_type", MaximumUnitTypeId() + 1},  // Cheating.
    });

std::vector<std::string> GetScreenFeatures() {
  std::vector<std::string> features;
  for (const auto& [k, v] : *kScreenFeaturesScale) {
    features.push_back(k);
  }
  std::sort(features.begin(), features.end());
  return features;
}

std::vector<std::string> GetMinimapFeatures() {
  std::vector<std::string> features;
  for (const auto& [k, v] : *kMinimapFeaturesScale) {
    // Filter out cheating observations.
    if (strcmp(k.c_str(), "buildable") != 0 &&
        strcmp(k.c_str(), "unit_type") != 0) {
      features.push_back(k);
    }
  }
  std::sort(features.begin(), features.end());
  return features;
}

absl::StatusOr<int> GetScreenFeatureScale(const absl::string_view name) {
  auto result = kScreenFeaturesScale->find(name);
  if (result == kScreenFeaturesScale->end()) {
    return absl::InvalidArgumentError(
        absl::StrCat("Can't find screen feature ", name));
  }
  return result->second;
}

absl::StatusOr<int> GetMinimapFeatureScale(const absl::string_view name) {
  auto result = kMinimapFeaturesScale->find(name);
  if (result == kMinimapFeaturesScale->end()) {
    return absl::InvalidArgumentError(
        absl::StrCat("Can't find minimap feature ", name));
  }
  return result->second;
}

}  // namespace pysc2
