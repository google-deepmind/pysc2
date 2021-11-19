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

#include "pysc2/env/converter/cc/unit_lookups.h"

#include "glog/logging.h"
#include "absl/container/flat_hash_map.h"
#include "pysc2/env/converter/cc/game_data/proto/units.pb.h"
#include "s2clientprotocol/common.pb.h"

namespace pysc2 {
namespace {

absl::flat_hash_map<uint32_t, SC2APIProtocol::Race>* UnitsToRace() {
  absl::flat_hash_map<uint32_t, SC2APIProtocol::Race>* unit_to_race =
      new absl::flat_hash_map<uint32_t, SC2APIProtocol::Race>();
  for (int i = 0; i < Protoss_descriptor()->value_count(); ++i) {
    auto u = Protoss_descriptor()->value(i)->number();
    unit_to_race->try_emplace(u, SC2APIProtocol::Protoss);
  }

  for (int i = 0; i < Terran_descriptor()->value_count(); ++i) {
    auto u = Terran_descriptor()->value(i)->number();
    unit_to_race->try_emplace(u, SC2APIProtocol::Terran);
  }

  for (int i = 0; i < Zerg_descriptor()->value_count(); ++i) {
    auto u = Zerg_descriptor()->value(i)->number();
    unit_to_race->try_emplace(u, SC2APIProtocol::Zerg);
  }

  for (int i = 0; i < Neutral_descriptor()->value_count(); ++i) {
    auto u = Neutral_descriptor()->value(i)->number();
    unit_to_race->try_emplace(u, SC2APIProtocol::NoRace);
  }

  return unit_to_race;
}

const absl::flat_hash_map<uint32_t, SC2APIProtocol::Race>& UnitToRaceMap() {
  static const auto* const units_to_race = UnitsToRace();
  return *units_to_race;
}

}  // namespace

SC2APIProtocol::Race UnitTypeToRace(uint32_t unit_type) {
  const auto& unit_to_race = UnitToRaceMap();
  const auto it = unit_to_race.find(unit_type);
  CHECK(it != unit_to_race.end()) << "Unknown unit type: " << unit_type;
  return it->second;
}

std::string UnitTypeToString(uint32_t unit_type) {
  SC2APIProtocol::Race race = UnitTypeToRace(unit_type);
  switch (race) {
    case SC2APIProtocol::Protoss:
      return Protoss_Name(unit_type);
    case SC2APIProtocol::Terran:
      return Terran_Name(unit_type);
    case SC2APIProtocol::Zerg:
      return Zerg_Name(unit_type);
    case SC2APIProtocol::Random:
    case SC2APIProtocol::NoRace:
      LOG(FATAL) << "Resolving unit type id to label is only implemented for "
                    "Protoss, Terran and Zerg units.";
  }
}

}  // namespace pysc2
