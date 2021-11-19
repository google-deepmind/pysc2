load("@my_deps//:requirements.bzl", "requirement")

package(default_visibility = ["//visibility:public"])

licenses(["notice"])  # Apache2 license

py_binary(
    name = "replay_actions",
    srcs = ["replay_actions.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        "//pysc2/lib:features",
        "//pysc2/lib:gfile",
        "//pysc2/lib:point",
        "//pysc2/lib:protocol",
        "//pysc2/lib:remote_controller",
        "//pysc2/lib:replay",
        "//pysc2/lib:static_data",
        "//pysc2/maps",  # build_cleaner: keep
        "//pysc2/run_configs",
        "@absl_py//absl:app",
        "@absl_py//absl/flags",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_binary(
    name = "gen_actions",
    srcs = ["gen_actions.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        "//pysc2/lib:static_data",
        "//pysc2/maps",
        "//pysc2/run_configs",
        "@absl_py//absl:app",
        "@absl_py//absl/flags",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_binary(
    name = "gen_data",
    srcs = ["gen_data.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        "//pysc2/lib:static_data",
        "//pysc2/maps",
        "//pysc2/run_configs",
        "@absl_py//absl:app",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_binary(
    name = "check_apm",
    srcs = ["check_apm.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        "//pysc2/lib:actions",
        "//pysc2/lib:features",
        "//pysc2/lib:point",
        "//pysc2/lib:units",
        "//pysc2/maps",
        "//pysc2/run_configs",
        "@absl_py//absl:app",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_binary(
    name = "benchmark_observe",
    srcs = ["benchmark_observe.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        "//pysc2/lib:replay",
        "//pysc2/lib:stopwatch",
        "//pysc2/maps",
        "//pysc2/run_configs",
        "@absl_py//absl:app",
        "@absl_py//absl/flags",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_binary(
    name = "benchmark_replay",
    srcs = ["benchmark_replay.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        "//pysc2/lib:actions",
        "//pysc2/lib:features",
        "//pysc2/lib:point_flag",
        "//pysc2/lib:replay",
        "//pysc2/lib:stopwatch",
        "//pysc2/run_configs",
        "@absl_py//absl:app",
        "@absl_py//absl/flags",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_binary(
    name = "mem_leak_check",
    srcs = ["mem_leak_check.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        "@absl_py//absl:app",
        "@absl_py//absl/flags",
        requirement("psutil"),  # build_cleaner: keep
        "//pysc2/lib:protocol",
        "//pysc2/maps",
        "//pysc2/run_configs",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_binary(
    name = "gen_versions",
    srcs = ["gen_versions.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        "@absl_py//absl:app",
        requirement("requests"),
    ],
)

py_binary(
    name = "map_list",
    srcs = ["map_list.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        "//pysc2/maps",
        "@absl_py//absl:app",
    ],
)

py_binary(
    name = "play",
    srcs = ["play.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        "//pysc2/env:sc2_env",
        "//pysc2/lib:point_flag",
        "//pysc2/lib:renderer_human",
        "//pysc2/lib:replay",
        "//pysc2/lib:stopwatch",
        "//pysc2/maps",
        "//pysc2/run_configs",
        "@absl_py//absl:app",
        "@absl_py//absl/flags",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_binary(
    name = "play_vs_agent",
    srcs = ["play_vs_agent.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        "@absl_py//absl:app",
        "@absl_py//absl/flags",
        requirement("portpicker"),
        "//pysc2/agents",  # build_cleaner: keep
        "//pysc2/env:lan_sc2_env",
        "//pysc2/env:run_loop",
        "//pysc2/env:sc2_env",
        "//pysc2/lib:point_flag",
        "//pysc2/lib:renderer_human",
        "//pysc2/maps",
        "//pysc2/run_configs",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_binary(
    name = "agent_remote",
    srcs = ["agent_remote.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        "//pysc2/agents",  # build_cleaner: keep
        "//pysc2/env:remote_sc2_env",
        "//pysc2/env:run_loop",
        "//pysc2/env:sc2_env",
        "//pysc2/lib:point_flag",
        "//pysc2/lib:portspicker",
        "//pysc2/lib:renderer_human",
        "//pysc2/maps",
        "//pysc2/run_configs",
        "@absl_py//absl:app",
        "@absl_py//absl/flags",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_binary(
    name = "replay_info",
    srcs = ["replay_info.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        "//pysc2/lib:gfile",
        "//pysc2/lib:remote_controller",
        "//pysc2/lib:replay",
        "//pysc2/run_configs",
        "@absl_py//absl:app",
        "@absl_py//absl/flags",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_binary(
    name = "agent",
    srcs = ["agent.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        "//pysc2/agents",  # build_cleaner: keep
        "//pysc2/env:available_actions_printer",
        "//pysc2/env:run_loop",
        "//pysc2/env:sc2_env",
        "//pysc2/lib:point_flag",
        "//pysc2/lib:stopwatch",
        "//pysc2/maps",
        "@absl_py//absl:app",
        "@absl_py//absl/flags",
    ],
)

py_binary(
    name = "valid_actions",
    srcs = ["valid_actions.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        "//pysc2/lib:actions",
        "//pysc2/lib:features",
        "//pysc2/lib:point_flag",
        "@absl_py//absl:app",
        "@absl_py//absl/flags",
    ],
)

py_binary(
    name = "compare_binaries",
    srcs = ["compare_binaries.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        "//pysc2/lib:image_differencer",
        "//pysc2/lib:proto_diff",
        "//pysc2/lib:remote_controller",
        "//pysc2/lib:replay",
        "//pysc2/lib:stopwatch",
        "//pysc2/run_configs",
        "@absl_py//absl:app",
        "@absl_py//absl/flags",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_binary(
    name = "battle_net_maps",
    srcs = ["battle_net_maps.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        "//pysc2/run_configs",
        "@absl_py//absl:app",
    ],
)

py_binary(
    name = "reencode_replays",
    srcs = ["reencode_replays.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        "//pysc2/lib:replay",
        "//pysc2/run_configs",
        "@absl_py//absl:app",
        "@absl_py//absl/flags",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_binary(
    name = "update_battle_net_cache",
    srcs = ["update_battle_net_cache.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        "@absl_py//absl:app",
        "@absl_py//absl/flags",
        requirement("mpyq"),
        "//pysc2/run_configs",
        "@s2protocol//:versions",
    ],
)
