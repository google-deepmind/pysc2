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
  absl::StatusOr<absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>>
  ConvertObservation(const pysc2::Observation& observation) {
    auto result = converter_.ConvertObservation(observation);
    return result;
  }
  absl::StatusOr<pysc2::Action> ConvertAction(
      const absl::flat_hash_map<std::string, dm_env_rpc::v1::Tensor>& action) {
    auto result = converter_.ConvertAction(action);
    return result;
  }
};

absl::StatusOr<ConverterWrapper> MakeConverterWrapper(
    const std::string& settings, const std::string& environment_info) {
  // Deserialize strings.
  pysc2::EnvironmentInfo env_info;
  pysc2::ConverterSettings converter_settings;
  converter_settings.ParseFromString(settings);
  env_info.ParseFromString(environment_info);
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
