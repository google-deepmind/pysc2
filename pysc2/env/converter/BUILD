load("@my_deps//:requirements.bzl", "requirement")

package(default_visibility = ["//visibility:public"])

licenses(["notice"])

py_library(
    name = "converter",
    srcs = ["converter.py"],
    data = ["//pysc2/env/converter/cc/python:converter.so"],
    deps = [
        "//pysc2/env/converter/proto:converter_py_pb2",
        "@dm_env_archive//:dm_env",
        "@dm_env_rpc_archive//:dm_env_rpc",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_test(
    name = "converter_test",
    srcs = ["converter_test.py"],
    legacy_create_init = False,
    deps = [
        ":converter",
        "@absl_py//absl/testing:absltest",
        "@absl_py//absl/testing:parameterized",
        requirement("numpy"),
        "//pysc2/env/converter/proto:converter_py_pb2",
        "@s2client_proto//s2clientprotocol:common_py_pb2",
        "@s2client_proto//s2clientprotocol:raw_py_pb2",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
        "@s2client_proto//s2clientprotocol:spatial_py_pb2",
    ],
)

py_library(
    name = "derive_interface_options",
    srcs = ["derive_interface_options.py"],
    srcs_version = "PY3",
    deps = [
        "//pysc2/env/converter/proto:converter_py_pb2",
        "@s2client_proto//s2clientprotocol:common_py_pb2",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_library(
    name = "__init__",
    srcs = ["__init__.py"],
)
