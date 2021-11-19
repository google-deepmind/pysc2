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

#ifndef PYSC2_ENV_CONVERTER_CC_CHECK_PROTOS_EQUAL_H_
#define PYSC2_ENV_CONVERTER_CC_CHECK_PROTOS_EQUAL_H_

#include <string>

#include "google/protobuf/util/message_differencer.h"
#include "absl/status/status.h"

namespace pysc2 {

// Returns OK if the passed protos are equal according to message differencer,
// an InvalidArgumentError with the differences string otherwise.
template <typename T>
absl::Status CheckProtosEqual(const T& a, const T& b) {
  google::protobuf::util::MessageDifferencer message_differencer;
  std::string differences;
  message_differencer.ReportDifferencesToString(&differences);
  if (message_differencer.Compare(a, b)) {
    return absl::OkStatus();
  } else {
    return absl::InvalidArgumentError(differences);
  }
}

}  // namespace pysc2

#endif  // PYSC2_ENV_CONVERTER_CC_CHECK_PROTOS_EQUAL_H_
