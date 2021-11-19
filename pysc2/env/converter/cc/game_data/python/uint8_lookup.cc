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

#include "pysc2/env/converter/cc/game_data/uint8_lookup.h"

#include "pybind11/pybind11.h"

PYBIND11_MODULE(uint8_lookup, m) {
  m.doc() = "uint8_lookup bindings.";

  m.def("PySc2ToUint8", &pysc2::PySc2ToUint8, pybind11::arg("data"));
  m.def("PySc2ToUint8Buffs", &pysc2::PySc2ToUint8Buffs, pybind11::arg("data"));
  m.def("PySc2ToUint8Upgrades", &pysc2::PySc2ToUint8Upgrades,
        pybind11::arg("data"));
  m.def("MaximumUnitTypeId", &pysc2::MaximumUnitTypeId);
  m.def("MaximumBuffId", &pysc2::MaximumBuffId);
  m.def("Uint8ToPySc2", &pysc2::Uint8ToPySc2, pybind11::arg("utype"));
  m.def("Uint8ToPySc2Upgrades", &pysc2::Uint8ToPySc2Upgrades,
        pybind11::arg("upgrade_type"));
  m.def("EffectIdIdentity", &pysc2::EffectIdIdentity,
        pybind11::arg("effect_id"));
}
