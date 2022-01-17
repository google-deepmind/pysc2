load("@my_deps//:requirements.bzl", "requirement")
load("//pysc2:build_defs.bzl", "pytype_library")

package(default_visibility = ["//visibility:public"])

licenses(["notice"])  # Apache2 license

py_library(
    name = "dummy_observation",
    srcs = ["dummy_observation.py"],
    srcs_version = "PY3",
    deps = [
        requirement("numpy"),
        "//pysc2/lib:features",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_test(
    name = "dummy_observation_test",
    size = "small",
    srcs = ["dummy_observation_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":dummy_observation",
        "@absl_py//absl/testing:absltest",
        "@absl_py//absl/testing:parameterized",
        requirement("numpy"),
        "//pysc2/lib:actions",
        "//pysc2/lib:features",
        "//pysc2/lib:point",
        "//pysc2/lib:units",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_test(
    name = "debug_test",
    size = "enormous",
    srcs = ["debug_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        "//pysc2/lib:units",
        "//pysc2/maps",
        "//pysc2/run_configs",
        "@absl_py//absl/testing:absltest",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_test(
    name = "easy_scripted_test",
    size = "enormous",
    srcs = ["easy_scripted_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":utils",
        "//pysc2/agents:scripted_agent",
        "//pysc2/env:run_loop",
        "//pysc2/env:sc2_env",
        "@absl_py//absl/testing:absltest",
    ],
)

py_test(
    name = "actions_test",
    size = "enormous",
    srcs = ["actions_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":utils",
        "//pysc2/lib:actions",
        "//pysc2/lib:units",
        "@absl_py//absl/testing:absltest",
    ],
)

py_test(
    name = "obs_test",
    size = "enormous",
    srcs = ["obs_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    shard_count = 5,
    srcs_version = "PY3",
    deps = [
        ":utils",
        "//pysc2/lib:actions",
        "//pysc2/lib:buffs",
        "//pysc2/lib:features",
        "//pysc2/lib:units",
        "@absl_py//absl/testing:absltest",
        "@s2client_proto//s2clientprotocol:debug_py_pb2",
        "@s2client_proto//s2clientprotocol:raw_py_pb2",
    ],
)

py_test(
    name = "host_remote_agent_test",
    size = "enormous",
    srcs = ["host_remote_agent_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":utils",
        "//pysc2/env:host_remote_agent",
        "//pysc2/lib:remote_controller",
        "//pysc2/lib:run_parallel",
        "@absl_py//absl/testing:absltest",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_test(
    name = "multi_player_test",
    size = "enormous",
    srcs = ["multi_player_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":utils",
        "//pysc2/lib:point",
        "//pysc2/lib:portspicker",
        "//pysc2/lib:run_parallel",
        "//pysc2/maps",
        "//pysc2/run_configs",
        "@absl_py//absl/logging",
        "@absl_py//absl/testing:absltest",
        "@s2client_proto//s2clientprotocol:common_py_pb2",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_test(
    name = "multi_player_env_test",
    size = "enormous",
    srcs = ["multi_player_env_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    shard_count = 3,
    srcs_version = "PY3",
    deps = [
        ":utils",
        "//pysc2/agents:no_op_agent",
        "//pysc2/agents:random_agent",
        "//pysc2/env:run_loop",
        "//pysc2/env:sc2_env",
        "@absl_py//absl/testing:absltest",
        "@absl_py//absl/testing:parameterized",
        "@s2client_proto//s2clientprotocol:common_py_pb2",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_test(
    name = "observer_test",
    size = "enormous",
    srcs = ["observer_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":utils",
        "//pysc2/maps",
        "//pysc2/run_configs",
        "@absl_py//absl/testing:absltest",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_test(
    name = "protocol_error_test",
    size = "enormous",
    srcs = ["protocol_error_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":utils",
        "//pysc2/lib:protocol",
        "//pysc2/lib:remote_controller",
        "//pysc2/maps",
        "//pysc2/run_configs",
        "@absl_py//absl/testing:absltest",
        "@s2client_proto//s2clientprotocol:common_py_pb2",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_test(
    name = "random_agent_test",
    size = "enormous",
    srcs = ["random_agent_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    shard_count = 3,
    srcs_version = "PY3",
    deps = [
        ":utils",
        "//pysc2/agents:random_agent",
        "//pysc2/env:run_loop",
        "//pysc2/env:sc2_env",
        "@absl_py//absl/testing:absltest",
        "@absl_py//absl/testing:parameterized",
    ],
)

py_test(
    name = "obs_spec_test",
    size = "enormous",
    srcs = ["obs_spec_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":utils",
        "//pysc2/agents:random_agent",
        "//pysc2/env:sc2_env",
        "@absl_py//absl/testing:absltest",
    ],
)

py_test(
    name = "render_test",
    size = "enormous",
    srcs = ["render_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":utils",
        "@absl_py//absl/testing:absltest",
        requirement("numpy"),
        "//pysc2/lib:features",
        "//pysc2/maps",
        "//pysc2/run_configs",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_test(
    name = "ping_test",
    size = "enormous",
    srcs = ["ping_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":utils",
        "//pysc2/lib:stopwatch",
        "//pysc2/run_configs",
        "@absl_py//absl/testing:absltest",
    ],
)

py_test(
    name = "general_actions_test",
    size = "enormous",
    srcs = ["general_actions_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":utils",
        "//pysc2/lib:actions",
        "//pysc2/maps",
        "//pysc2/run_configs",
        "@absl_py//absl/testing:absltest",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_test(
    name = "replay_obs_test",
    size = "enormous",
    srcs = ["replay_obs_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":utils",
        "//pysc2/lib:actions",
        "//pysc2/lib:features",
        "//pysc2/lib:point",
        "//pysc2/lib:renderer_ascii",
        "//pysc2/lib:units",
        "//pysc2/maps",
        "//pysc2/run_configs",
        "@absl_py//absl/testing:absltest",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_test(
    name = "step_mul_override_test",
    size = "enormous",
    srcs = ["step_mul_override_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":utils",
        "//pysc2/env:sc2_env",
        "//pysc2/lib:actions",
        "@absl_py//absl/testing:absltest",
    ],
)

pytype_library(
    name = "utils",
    testonly = 1,
    srcs = ["utils.py"],
    srcs_version = "PY3",
    deps = [
        "//pysc2/lib:actions",
        "//pysc2/lib:features",
        "//pysc2/lib:point",
        "//pysc2/lib:portspicker",
        "//pysc2/lib:run_parallel",
        "//pysc2/lib:stopwatch",
        "//pysc2/maps",
        "//pysc2/run_configs",
        "@absl_py//absl/logging",
        "@absl_py//absl/testing:absltest",
        "@s2client_proto//s2clientprotocol:common_py_pb2",
        "@s2client_proto//s2clientprotocol:debug_py_pb2",
        "@s2client_proto//s2clientprotocol:error_py_pb2",
        "@s2client_proto//s2clientprotocol:raw_py_pb2",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_test(
    name = "versions_test",
    size = "enormous",
    srcs = ["versions_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        "//pysc2/maps",
        "//pysc2/run_configs",
        "@absl_py//absl/logging",
        "@absl_py//absl/testing:absltest",
        "@s2client_proto//s2clientprotocol:common_py_pb2",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

pytype_library(
    name = "__init__",
    srcs = ["__init__.py"],
    srcs_version = "PY3",
)
