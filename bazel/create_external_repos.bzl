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

"""Creates external repos needed by PySC2 and by its consumers."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

def pysc2_create_external_repos(pysc2_repo_name):
    """Creates external repos needed by PySC2 and by its consumers.

    Args:
        pysc2_repo_name: The name of the PySC2 repo, as instantiated in
          the local WORKSPACE. When executing this function from the pysc2
          WORKSPACE, this name is "pysc2". But external consumers shouldn't
          use that name as it leads to Python import problems due to the
          pysc2/pysc2 subdirectory. Hence a name such as "pysc2_archive"
          is recommended.

    Example:
        http_archive(
            name = "pysc2_archive",
            # ...
        )

        load("@pysc2_archive//bazel:create_external_repos.bzl",
             "pysc2_create_external_repos")
        pysc2_create_external_repos(pysc2_repo_name = "pysc2_archive")
    """

    if not native.existing_rule("absl_py"):
        # It is important that this isn't named simply 'absl' as the project has a
        # subdirectory named that, and Python module lookup fails if we have absl/absl.
        http_archive(
            name = "absl_py",
            strip_prefix = "abseil-py-main",
            urls = ["https://github.com/abseil/abseil-py/archive/main.zip"],
        )

    # Required by glog.
    if not native.existing_rule("com_github_gflags_gflags"):
        http_archive(
            name = "com_github_gflags_gflags",
            sha256 = "34af2f15cf7367513b352bdcd2493ab14ce43692d2dcd9dfc499492966c64dcf",
            strip_prefix = "gflags-2.2.2",
            urls = [
                "https://github.com/gflags/gflags/archive/v2.2.2.tar.gz",
            ],
        )

    if not native.existing_rule("glog"):
        http_archive(
            name = "glog",
            sha256 = "6281aa4eeecb9e932d7091f99872e7b26fa6aacece49c15ce5b14af2b7ec050f",
            urls = [
                "https://github.com/google/glog/archive/96a2f23dca4cc7180821ca5f32e526314395d26a.zip",
            ],
            strip_prefix = "glog-96a2f23dca4cc7180821ca5f32e526314395d26a",
        )

    if not native.existing_rule("com_google_protobuf"):
        http_archive(
            name = "com_google_protobuf",
            patches = ["@" + pysc2_repo_name + "//bazel:protobuf.patch"],
            urls = ["https://github.com/protocolbuffers/protobuf/archive/refs/tags/v3.19.1.zip"],
            strip_prefix = "protobuf-3.19.1",
        )

    if not native.existing_rule("com_google_googleapis"):
        http_archive(
            name = "com_google_googleapis",
            sha256 = "1f742f6cafe616fe73302db010e0b7ee6579cb1ce06010427b7d0995cbd80ce4",
            strip_prefix = "googleapis-6a813acf535e4746fa4a135ce23547bb6425c26d",
            urls = [
                "https://github.com/googleapis/googleapis/archive/6a813acf535e4746fa4a135ce23547bb6425c26d.tar.gz",
            ],
        )

    if not native.existing_rule("pybind11_abseil"):
        http_archive(
            name = "pybind11_abseil",
            urls = ["https://github.com/pybind/pybind11_abseil/archive/28f46a10d9db25159ecab04a1d3349cd25e68797.tar.gz"],
            strip_prefix = "pybind11_abseil-28f46a10d9db25159ecab04a1d3349cd25e68797",
        )

    if not native.existing_rule("pybind11_bazel"):
        http_archive(
            name = "pybind11_bazel",
            strip_prefix = "pybind11_bazel-master",
            urls = ["https://github.com/pybind/pybind11_bazel/archive/refs/heads/master.zip"],
        )

    if not native.existing_rule("pybind11"):
        http_archive(
            name = "pybind11",
            build_file = "@pybind11_bazel//:pybind11.BUILD",
            strip_prefix = "pybind11-2.8.1",
            urls = ["https://github.com/pybind/pybind11/archive/v2.8.1.tar.gz"],
        )

    if not native.existing_rule("s2client_proto"):
        http_archive(
            name = "s2client_proto",
            urls = ["https://github.com/Blizzard/s2client-proto/archive/refs/heads/master.zip"],
            strip_prefix = "s2client-proto-master",
            patches = ["@" + pysc2_repo_name + "//bazel:s2clientprotocol.patch"],
        )

    if not native.existing_rule("s2protocol_archive"):
        http_archive(
            name = "s2protocol_archive",
            urls = ["https://github.com/Blizzard/s2protocol/archive/refs/heads/master.zip"],
            strip_prefix = "s2protocol-master",
            build_file = "@" + pysc2_repo_name + "//bazel:BUILD.s2protocol",
        )

    if not native.existing_rule("dm_env_archive"):
        # We can't use the wheels for dm_env because that pulls in
        # proto code which leads to incompatibilities with our our protos.
        http_archive(
            name = "dm_env_archive",
            urls = ["https://github.com/deepmind/dm_env/archive/refs/heads/master.zip"],
            strip_prefix = "dm_env-master",
            build_file = "@" + pysc2_repo_name + "//bazel:BUILD.dm_env",
        )

    if not native.existing_rule("dm_env_rpc_archive"):
        # We can't use the wheels for dm_env_rpc because that pulls in
        # proto code which leads to incompatibilities with our our protos.
        http_archive(
            name = "dm_env_rpc_archive",
            urls = ["https://github.com/deepmind/dm_env_rpc/archive/refs/heads/master.zip"],
            strip_prefix = "dm_env_rpc-master",
            build_file = "@" + pysc2_repo_name + "//bazel:BUILD.dm_env_rpc",
        )

    if not native.existing_rule("com_github_grpc_grpc"):
        http_archive(
            name = "com_github_grpc_grpc",
            strip_prefix = "grpc-master",
            urls = ["https://github.com/grpc/grpc/archive/refs/heads/master.zip"],
        )
