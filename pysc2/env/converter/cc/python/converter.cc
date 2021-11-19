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

#include "pysc2/env/converter/proto/converter.pb.h"
#include "pybind11/pybind11.h"
#include "pybind11_abseil/absl_casters.h"
#include "pybind11_abseil/status_casters.h"
#include "pybind11_protobuf/native_proto_caster.h"

PYBIND11_MODULE(converter, m) {
  pybind11_protobuf::ImportNativeProtoCasters();
  pybind11::google::ImportStatusModule();

  m.doc() = "Observation/action converter bindings.";

  pybind11::class_<pysc2::Converter>(m, "Converter")
      .def("ObservationSpec", &pysc2::Converter::ObservationSpec)
      .def("ActionSpec", &pysc2::Converter::ActionSpec)
      .def("ConvertObservation", &pysc2::Converter::ConvertObservation,
           pybind11::arg("observation"))
      .def("ConvertAction", &pysc2::Converter::ConvertAction,
           pybind11::arg("action"));

  m.def("MakeConverter", &pysc2::MakeConverter, pybind11::arg("settings"),
        pybind11::arg("environment_info"));
}
