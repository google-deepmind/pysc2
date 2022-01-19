load("@my_deps//:requirements.bzl", "requirement")
load("//pysc2:build_defs.bzl", "pytype_strict_library")

package(default_visibility = ["//visibility:public"])

licenses(["notice"])

exports_files([
    "test_data/replay_0" + str(i) + ".SC2Replay"
    for i in range(1, 10)
])

exports_files([
    "test_data/replay_0" + str(i) + ".skips.txt"
    for i in range(1, 10)
])

pytype_strict_library(
    name = "replay_converter",
    srcs = ["replay_converter.py"],
    srcs_version = "PY3",
    deps = [
        ":replay_observation_stream",
        ":sc2_replay",
        ":sc2_replay_utils",
        requirement("numpy"),
        "//pysc2/env/converter",
        "//pysc2/env/converter:derive_interface_options",
        "//pysc2/env/converter/proto:converter_py_pb2",
        requirement("dm-tree"),
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

pytype_strict_library(
    name = "replay_observation_stream",
    srcs = ["replay_observation_stream.py"],
    srcs_version = "PY3",
    deps = [
        "@absl_py//absl/logging",
        requirement("mpyq"),
        "//pysc2/run_configs",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

pytype_strict_library(
    name = "sc2_replay",
    srcs = ["sc2_replay.py"],
    srcs_version = "PY3",
    deps = [
        requirement("mpyq"),
        "@s2protocol_archive//:versions",
        requirement("dm-tree"),
    ],
)

py_test(
    name = "sc2_replay_test",
    srcs = ["sc2_replay_test.py"],
    data = ["//pysc2/lib/replay:test_data/replay_01.SC2Replay"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":sc2_replay",
        "//pysc2/lib:gfile",
        "//pysc2/lib:resources",
        "@absl_py//absl/flags",
        "@absl_py//absl/testing:absltest",
    ],
)

pytype_strict_library(
    name = "sc2_replay_utils",
    srcs = ["sc2_replay_utils.py"],
    srcs_version = "PY3",
    deps = [":sc2_replay"],
)

py_test(
    name = "sc2_replay_utils_test",
    srcs = ["sc2_replay_utils_test.py"],
    data = [
        "//pysc2/lib/replay:test_data/replay_0" + str(i) + ".SC2Replay"
        for i in range(1, 10)
    ] + [
        "//pysc2/lib/replay:test_data/replay_0" + str(i) + ".skips.txt"
        for i in range(1, 10)
    ],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":sc2_replay",
        ":sc2_replay_utils",
        "//pysc2/lib:gfile",
        "//pysc2/lib:resources",
        "@absl_py//absl/flags",
        "@absl_py//absl/testing:absltest",
        "@absl_py//absl/testing:parameterized",
    ],
)
