load("@my_deps//:requirements.bzl", "requirement")
load("//pysc2:build_defs.bzl", "pytype_library")

package(default_visibility = ["//visibility:public"])

licenses(["notice"])

pytype_library(
    name = "available_actions_printer",
    srcs = ["available_actions_printer.py"],
    srcs_version = "PY3",
    deps = [":base_env_wrapper"],
)

pytype_library(
    name = "base_env_wrapper",
    srcs = ["base_env_wrapper.py"],
    srcs_version = "PY3",
    deps = [":environment"],
)

pytype_library(
    name = "converted_env",
    srcs = ["converted_env.py"],
    deps = [
        "@dm_env_archive//:dm_env",
        requirement("numpy"),
        "//pysc2/env/converter",
        "//pysc2/env/converter/proto:converter_py_pb2",
        "//pysc2/lib:actions",
        requirement("dm-tree"),
        requirement("typing_extensions"),
        "@s2client_proto//s2clientprotocol:common_py_pb2",
        "@s2client_proto//s2clientprotocol:raw_py_pb2",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_test(
    name = "converted_env_test",
    srcs = ["converted_env_test.py"],
    legacy_create_init = False,
    deps = [
        ":converted_env",
        "@absl_py//absl/testing:absltest",
        "@dm_env_archive//:dm_env",
        "@dm_env_archive//:test_utils",
        requirement("numpy"),
        "//pysc2/env:mock_sc2_env",
        "//pysc2/env:sc2_env",
        "//pysc2/env/converter",
        "//pysc2/env/converter/proto:converter_py_pb2",
        "//pysc2/lib:features",
        "@s2client_proto//s2clientprotocol:common_py_pb2",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

pytype_library(
    name = "enums",
    srcs = ["enums.py"],
    srcs_version = "PY3",
    deps = [
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

pytype_library(
    name = "environment",
    srcs = ["environment.py"],
    srcs_version = "PY3",
)

pytype_library(
    name = "host_remote_agent",
    srcs = ["host_remote_agent.py"],
    srcs_version = "PY3",
    deps = [
        "//pysc2/lib:portspicker",
        "//pysc2/lib:protocol",
        "//pysc2/lib:remote_controller",
        "//pysc2/maps",
        "//pysc2/run_configs",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

pytype_library(
    name = "sc2_env",
    srcs = ["sc2_env.py"],
    srcs_version = "PY3",
    deps = [
        ":enums",
        ":environment",
        "//pysc2/lib:actions",
        "//pysc2/lib:features",
        "//pysc2/lib:metrics",
        "//pysc2/lib:portspicker",
        "//pysc2/lib:renderer_human",
        "//pysc2/lib:run_parallel",
        "//pysc2/lib:stopwatch",
        "//pysc2/maps",
        "//pysc2/run_configs",
        "@absl_py//absl/logging",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_test(
    name = "sc2_env_test",
    size = "small",
    srcs = ["sc2_env_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":sc2_env",
        "@absl_py//absl/testing:absltest",
        "@absl_py//absl/testing:parameterized",
    ],
)

pytype_library(
    name = "remote_sc2_env",
    srcs = ["remote_sc2_env.py"],
    srcs_version = "PY3",
    deps = [
        ":sc2_env",
        "//pysc2/lib:features",
        "//pysc2/lib:remote_controller",
        "//pysc2/lib:run_parallel",
        "//pysc2/maps",
        "//pysc2/run_configs",
        "@absl_py//absl/logging",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

pytype_library(
    name = "lan_sc2_env",
    srcs = ["lan_sc2_env.py"],
    srcs_version = "PY3",
    deps = [
        ":sc2_env",
        "//pysc2/lib:features",
        "//pysc2/lib:run_parallel",
        "//pysc2/run_configs",
        "@absl_py//absl/logging",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

pytype_library(
    name = "mock_sc2_env",
    srcs = ["mock_sc2_env.py"],
    srcs_version = "PY3",
    deps = [
        ":environment",
        ":sc2_env",
        requirement("numpy"),
        "//pysc2/lib:features",
        "//pysc2/lib:units",
        "//pysc2/tests:dummy_observation",
        "@s2client_proto//s2clientprotocol:common_py_pb2",
        "@s2client_proto//s2clientprotocol:raw_py_pb2",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_test(
    name = "mock_sc2_env_test",
    size = "small",
    srcs = ["mock_sc2_env_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":enums",
        ":environment",
        ":mock_sc2_env",
        ":sc2_env",
        "@absl_py//absl/testing:absltest",
        requirement("mock"),
        requirement("numpy"),
        "//pysc2/lib:features",
    ],
)

py_test(
    name = "mock_sc2_env_comparison_test",
    size = "large",
    srcs = ["mock_sc2_env_comparison_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":mock_sc2_env",
        ":sc2_env",
        "@absl_py//absl/testing:absltest",
    ],
)

pytype_library(
    name = "run_loop",
    srcs = ["run_loop.py"],
    srcs_version = "PY3",
)

pytype_library(
    name = "__init__",
    srcs = ["__init__.py"],
    srcs_version = "PY3",
)
