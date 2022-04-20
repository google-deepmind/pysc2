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

#include "pysc2/env/converter/cc/converter.h"

#include <memory>

#include "absl/status/statusor.h"
#include "absl/strings/string_view.h"
#include "dm_env_rpc/v1/dm_env_rpc.pb.h"
#include "pysc2/env/converter/proto/converter.pb.h"
#include "pybind11/pybind11.h"
#include "pybind11_abseil/absl_casters.h"
#include "pybind11_abseil/status_casters.h"
#include "pybind11_protobuf/native_proto_caster.h"

namespace {
class ConverterWrapper {
  // The wrapper serializes and deserializes protos at the
  // pybind11 boundaries since proto formats are inconsistent downstream
  // (eg. alphastar) with the bazel build of PySC2.
 private:
  pysc2::Converter converter_;

 public:
  ConverterWrapper(pysc2::Converter converter)
      : converter_(std::move(converter)) {}

  absl::flat_hash_map<std::string, pybind11::bytes> ObservationSpec() {
    absl::flat_hash_map<std::string, dm_env_rpc::v1::TensorSpec> spec;
    absl::flat_hash_map<std::string, pybind11::bytes> obs_spec;
    spec = converter_.ObservationSpec();
    for (const auto& p : spec) {
      std::string temp;
      p.second.SerializeToString(&temp);
      obs_spec[p.first] = temp;
    }
    return obs_spec;
  }
  absl::flat_hash_map<std::string, pybind11::bytes> ActionSpec() {
    absl::flat_hash_map<std::string, dm_env_rpc::v1::TensorSpec> spec;
    absl::flat_hash_map<std::string, pybind11::bytes> action_spec;
    spec = converter_.ActionSpec();
    for (const auto& p : spec) {
      std::string temp;
      p.second.SerializeToString(&temp);
      action_spec[p.first] = temp;
    }
    return action_spec;
  }
  absl::StatusOr<absl::flat_hash_map<std::string, pybind11::bytes>>
  ConvertObservation(const pybind11::bytes& observation) {
    pysc2::Observation deserialized_obs;
    absl::flat_hash_map<std::string, pybind11::bytes> serialized_obs;
    deserialized_obs.ParseFromString(observation);
    auto converted_obs_or = converter_.ConvertObservation(deserialized_obs);
    if (!converted_obs_or.ok()) {
      return converted_obs_or.status();
    }
    for (const auto& p : *converted_obs_or) {
      std::string temp;
      p.second.SerializeToString(&temp);
      serialized_obs[p.first] = temp;
    }
    return serialized_obs;
  }
  absl::StatusOr<pybind11::bytes> ConvertAction(
      const absl::flat_hash_map<std::string, pybind11::bytes>& action) {
    absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>
        deserialized_action;
    for (const auto& p : action) {
      dm_env_rpc::v1::Tensor temp;
      temp.ParseFromString(p.second);
      deserialized_action[p.first] = temp;
    }
    absl::StatusOr<pysc2::Action> converted_action_or;
    converted_action_or = converter_.ConvertAction(deserialized_action);
    if (!converted_action_or.ok()) {
      return converted_action_or.status();
    }
    std::string serialized_action;
    converted_action_or->SerializeToString(&serialized_action);
    return serialized_action;
  }
};

absl::StatusOr<ConverterWrapper> MakeConverterWrapper(
    absl::string_view settings, absl::string_view environment_info) {
  // Deserialize strings.
  pysc2::EnvironmentInfo env_info;
  pysc2::ConverterSettings converter_settings;
  converter_settings.ParseFromString(std::string(settings));
  env_info.ParseFromString(std::string(environment_info));
  absl::StatusOr<pysc2::Converter> converter_or =
      pysc2::MakeConverter(converter_settings, env_info);
  if (!converter_or.ok()) return converter_or.status();
  return ConverterWrapper(std::move(converter_or).value());
}
}  //  namespace

PYBIND11_MODULE(converter, m) {
  pybind11_protobuf::ImportNativeProtoCasters();
  pybind11::google::ImportStatusModule();

  m.doc() = "Observation/action converter bindings.";

  pybind11::class_<ConverterWrapper>(m, "Converter")
      .def("ObservationSpec", &ConverterWrapper::ObservationSpec)
      .def("ActionSpec", &ConverterWrapper::ActionSpec)
      .def("ConvertObservation", &ConverterWrapper::ConvertObservation,
           pybind11::arg("observation"))
      .def("ConvertAction", &ConverterWrapper::ConvertAction,
           pybind11::arg("action"));

  m.def("MakeConverter", &MakeConverterWrapper, pybind11::arg("settings"),
        pybind11::arg("environment_info"));
}
