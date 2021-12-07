# Copyright 2021 DeepMind Technologies Ltd. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Sets up external repos needed by PySC2 and by its consumers."""

load("@com_google_googleapis//:repository_rules.bzl", "switched_rules_by_language")
load("@com_github_grpc_grpc//bazel:grpc_deps.bzl", "grpc_deps")
load("@com_google_protobuf//:protobuf_deps.bzl", "protobuf_deps")
load("@pybind11_bazel//:python_configure.bzl", "python_configure")

def pysc2_setup_external_repos():
    """Sets up external repos needed by PySC2 and by its consumers.

    Ideally these would happen as part of pysc2_deps, but load statements are
    only permitted at the top level currently, necessitating this workaround.
    """
    protobuf_deps()
    switched_rules_by_language(
        name = "com_google_googleapis_imports",
        cc = True,
        python = True,
    )
    python_configure(name = "local_config_python")
    grpc_deps()
