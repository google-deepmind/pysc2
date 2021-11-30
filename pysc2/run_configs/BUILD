load("//pysc2:build_defs.bzl", "pytype_library")

package(default_visibility = ["//visibility:public"])

licenses(["notice"])  # Apache 2.0 License

pytype_library(
    name = "run_configs",
    srcs = ["__init__.py"],
    srcs_version = "PY3",
    deps = [
        ":lib",
        ":platforms",
        "//pysc2/lib:sc_process",
        "@absl_py//absl/flags",
    ],
)

pytype_library(
    name = "lib",
    srcs = ["lib.py"],
    srcs_version = "PY3",
    deps = [
        "//pysc2/lib:gfile",
    ],
)

pytype_library(
    name = "platforms",
    srcs = ["platforms.py"],
    deps = [
        ":lib",
        "//pysc2/lib:sc_process",
        "@absl_py//absl/flags",
        "@absl_py//absl/logging",
    ],
)
