load("//pysc2:build_defs.bzl", "pytype_strict_library")
load("@pybind11_bazel//:build_defs.bzl", "pybind_extension")

package(default_visibility = ["//visibility:public"])

licenses(["notice"])

pybind_extension(
    name = "converter",
    srcs = ["converter.cc"],
    copts = ["-fexceptions"],
    features = ["-use_header_modules"],
    deps = [
        "//pysc2/env/converter/cc:converter",
        "//pysc2/env/converter/proto:converter_cc_proto",
        "@com_google_absl//absl/status:statusor",
        "@com_google_absl//absl/strings",
        "@dm_env_rpc_archive//:dm_env_rpc_cc_proto",
    ],
)

pytype_strict_library(
    name = "__init__",
    srcs = ["__init__.py"],
)
