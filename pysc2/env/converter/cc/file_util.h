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

#ifndef PYSC2_ENV_CONVERTER_CC_PROTO_UTIL_H_
#define PYSC2_ENV_CONVERTER_CC_PROTO_UTIL_H_

#include "google/protobuf/message_lite.h"
#include "absl/status/status.h"
#include "absl/strings/string_view.h"

namespace pysc2 {

absl::Status GetBinaryProto(absl::string_view filename,
                            google::protobuf::MessageLite* proto);

absl::Status GetTextProto(absl::string_view filename, google::protobuf::Message* proto);

}  // namespace pysc2

#endif  // PYSC2_ENV_CONVERTER_CC_PROTO_UTIL_H_
