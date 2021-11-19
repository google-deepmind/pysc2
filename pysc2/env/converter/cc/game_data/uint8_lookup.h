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

#ifndef PYSC2_ENV_CONVERTER_CC_GAME_DATA_UINT8_LOOKUP_H_
#define PYSC2_ENV_CONVERTER_CC_GAME_DATA_UINT8_LOOKUP_H_

namespace pysc2 {

int PySc2ToUint8(int data);
int PySc2ToUint8Buffs(int data);
int PySc2ToUint8Upgrades(int data);
int MaximumUnitTypeId();
int MaximumBuffId();
int Uint8ToPySc2(int utype);
int Uint8ToPySc2Upgrades(int upgrade_type);
int EffectIdIdentity(int effect_id);

}  // namespace pysc2

#endif  // PYSC2_ENV_CONVERTER_GAME_DATA_UINT8_LOOKUP_H_
