load("@my_deps//:requirements.bzl", "requirement")
load("//pysc2:build_defs.bzl", "pytype_library")

package(default_visibility = ["//visibility:public"])

licenses(["notice"])  # Apache 2.0 License

py_library(
    name = "actions",
    srcs = ["actions.py"],
    srcs_version = "PY3",
    deps = [
        ":point",
        requirement("numpy"),
        "@s2client_proto//s2clientprotocol:spatial_py_pb2",
        "@s2client_proto//s2clientprotocol:ui_py_pb2",
    ],
)

pytype_library(
    name = "colors",
    srcs = ["colors.py"],
    srcs_version = "PY3",
    deps = [
        ":static_data",
        requirement("numpy"),
    ],
)

pytype_library(
    name = "named_array",
    srcs = ["named_array.py"],
    srcs_version = "PY3",
    deps = [
        requirement("numpy"),
    ],
)

pytype_library(
    name = "point_flag",
    srcs = ["point_flag.py"],
    srcs_version = "PY3",
    deps = [
        ":point",
        "@absl_py//absl/flags",
    ],
)

py_test(
    name = "named_array_test",
    size = "small",
    srcs = ["named_array_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":named_array",
        "@absl_py//absl/testing:absltest",
        "@absl_py//absl/testing:parameterized",
        requirement("numpy"),
    ],
)

pytype_library(
    name = "features",
    srcs = ["features.py"],
    srcs_version = "PY3",
    deps = [
        ":actions",
        ":colors",
        ":named_array",
        ":point",
        ":static_data",
        ":stopwatch",
        ":transform",
        "@absl_py//absl/logging",
        requirement("numpy"),
        "@s2client_proto//s2clientprotocol:raw_py_pb2",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_test(
    name = "features_test",
    size = "small",
    srcs = ["features_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":actions",
        ":features",
        ":point",
        "@absl_py//absl/testing:absltest",
        "@absl_py//absl/testing:parameterized",
        requirement("numpy"),
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

pytype_library(
    name = "gfile",
    srcs = ["gfile.py"],
)

pytype_library(
    name = "image_differencer",
    srcs = ["image_differencer.py"],
    srcs_version = "PY3",
    deps = [
        ":features",
        ":np_util",
        ":proto_diff",
        "@s2client_proto//s2clientprotocol:common_py_pb2",
    ],
)

py_test(
    name = "image_differencer_test",
    srcs = ["image_differencer_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":image_differencer",
        ":proto_diff",
        "@absl_py//absl/testing:absltest",
        requirement("numpy"),
        "@s2client_proto//s2clientprotocol:common_py_pb2",
    ],
)

pytype_library(
    name = "metrics",
    srcs = ["metrics.py"],
    srcs_version = "PY3",
)

pytype_library(
    name = "protocol",
    srcs = ["protocol.py"],
    srcs_version = "PY3",
    deps = [
        ":stopwatch",
        "@absl_py//absl/flags",
        "@absl_py//absl/logging",
        requirement("websocket-client"),
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

pytype_library(
    name = "memoize",
    srcs = ["memoize.py"],
    srcs_version = "PY3",
)

pytype_library(
    name = "np_util",
    srcs = ["np_util.py"],
    srcs_version = "PY3",
    deps = [
        requirement("numpy"),
    ],
)

py_test(
    name = "np_util_test",
    srcs = ["np_util_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":np_util",
        "@absl_py//absl/testing:absltest",
        "@absl_py//absl/testing:parameterized",
        requirement("numpy"),
    ],
)

pytype_library(
    name = "portspicker",
    srcs = ["portspicker.py"],
    srcs_version = "PY3",
    deps = [
        requirement("portpicker"),
    ],
)

py_test(
    name = "portspicker_test",
    size = "small",
    srcs = ["portspicker_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":portspicker",
        "@absl_py//absl/testing:absltest",
        "@absl_py//absl/testing:parameterized",
    ],
)

pytype_library(
    name = "proto_diff",
    srcs = ["proto_diff.py"],
    srcs_version = "PY3",
    deps = [requirement("deepdiff")],
)

py_test(
    name = "proto_diff_test",
    srcs = ["proto_diff_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":proto_diff",
        "@absl_py//absl/testing:absltest",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
        "@s2client_proto//s2clientprotocol:score_py_pb2",
    ],
)

pytype_library(
    name = "remote_controller",
    srcs = ["remote_controller.py"],
    srcs_version = "PY3",
    deps = [
        ":protocol",
        ":static_data",
        ":stopwatch",
        "@absl_py//absl/flags",
        "@absl_py//absl/logging",
        requirement("websocket-client"),
        "@s2client_proto//s2clientprotocol:debug_py_pb2",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

pytype_library(
    name = "renderer_human",
    srcs = ["renderer_human.py"],
    srcs_version = "PY3",
    deps = [
        ":buffs",
        ":colors",
        ":features",
        ":memoize",
        ":point",
        ":remote_controller",
        ":stopwatch",
        ":transform",
        ":video_writer",
        "@absl_py//absl/logging",
        requirement("numpy"),
        requirement("pygame"),
        "@s2client_proto//s2clientprotocol:error_py_pb2",
        "@s2client_proto//s2clientprotocol:raw_py_pb2",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
        "@s2client_proto//s2clientprotocol:spatial_py_pb2",
        "@s2client_proto//s2clientprotocol:ui_py_pb2",
    ],
)

pytype_library(
    name = "replay",
    srcs = ["replay.py"],
    srcs_version = "PY3",
    deps = [
        requirement("mpyq"),
        "//pysc2/run_configs:lib",
    ],
)

pytype_library(
    name = "resources",
    srcs = ["resources.py"],
)

pytype_library(
    name = "run_parallel",
    srcs = ["run_parallel.py"],
    srcs_version = "PY3",
)

py_test(
    name = "run_parallel_test",
    size = "small",
    srcs = ["run_parallel_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":run_parallel",
        "@absl_py//absl/testing:absltest",
    ],
)

pytype_library(
    name = "sc_process",
    srcs = ["sc_process.py"],
    srcs_version = "PY3",
    deps = [
        ":remote_controller",
        ":stopwatch",
        "@absl_py//absl/flags",
        "@absl_py//absl/logging",
        requirement("portpicker"),
    ],
)

pytype_library(
    name = "static_data",
    srcs = ["static_data.py"],
    srcs_version = "PY3",
)

pytype_library(
    name = "point",
    srcs = ["point.py"],
    srcs_version = "PY3",
)

py_test(
    name = "point_test",
    srcs = ["point_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":point",
        "@absl_py//absl/testing:absltest",
    ],
)

pytype_library(
    name = "stopwatch",
    srcs = ["stopwatch.py"],
    srcs_version = "PY3",
)

py_test(
    name = "stopwatch_test",
    srcs = ["stopwatch_test.py"],
    legacy_create_init = False,
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":stopwatch",
        "@absl_py//absl/testing:absltest",
        requirement("mock"),
    ],
)

pytype_library(
    name = "transform",
    srcs = ["transform.py"],
    srcs_version = "PY3",
    deps = [":point"],
)

pytype_library(
    name = "buffs",
    srcs = ["buffs.py"],
    srcs_version = "PY3",
)

pytype_library(
    name = "upgrades",
    srcs = ["upgrades.py"],
    srcs_version = "PY3",
)

pytype_library(
    name = "units",
    srcs = ["units.py"],
    srcs_version = "PY3",
)

pytype_library(
    name = "renderer_ascii",
    srcs = ["renderer_ascii.py"],
    srcs_version = "PY3",
    deps = [
        ":units",
    ],
)

pytype_library(
    name = "video_writer",
    srcs = ["video_writer.py"],
    srcs_version = "PY3",
    deps = [
        requirement("sk-video"),
    ],
)
