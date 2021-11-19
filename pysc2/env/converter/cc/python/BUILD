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
        "@pybind11_abseil//pybind11_abseil:absl_casters",
        "@pybind11_abseil//pybind11_abseil:status_casters",
        "@pybind11_protobuf//pybind11_protobuf:native_proto_caster",
    ],
)

py_library(
    name = "__init__",
    srcs = ["__init__.py"],
)
