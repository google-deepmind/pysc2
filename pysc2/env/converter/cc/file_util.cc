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

#include "pysc2/env/converter/cc/file_util.h"

#include <fstream>
#include <sstream>

#include "google/protobuf/message_lite.h"
#include "google/protobuf/text_format.h"
#include "absl/status/status.h"
#include "absl/strings/str_cat.h"
#include "absl/strings/string_view.h"

namespace pysc2 {

absl::Status GetBinaryProto(absl::string_view filename,
                            google::protobuf::MessageLite* proto) {
  std::ifstream file((std::string(filename)));
  if (!file) {
    return absl::NotFoundError(filename);
  }
  bool success = proto->ParseFromIstream(&file);
  file.close();

  if (success) {
    return absl::OkStatus();
  } else {
    return absl::InvalidArgumentError(
        absl::StrCat("Failed to parse binary proto from ", filename));
  }
}

absl::Status GetTextProto(absl::string_view filename, google::protobuf::Message* proto) {
  std::ifstream file((std::string(filename)));
  if (!file) {
    return absl::NotFoundError(filename);
  }
  std::stringstream buffer;
  buffer << file.rdbuf();
  bool success = google::protobuf::TextFormat::ParseFromString(buffer.str(), proto);
  file.close();
  if (success) {
    return absl::OkStatus();
  } else {
    return absl::InvalidArgumentError(
        absl::StrCat("Failed to parse text proto from ", buffer.str()));
  }
}

}  // namespace pysc2
