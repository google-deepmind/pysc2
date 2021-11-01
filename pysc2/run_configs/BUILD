package(default_visibility = ["//visibility:public"])

licenses(["notice"])  # Apache 2.0 License

py_library(
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

py_library(
    name = "lib",
    srcs = ["lib.py"],
    srcs_version = "PY3",
    deps = [
        "//pysc2/lib:gfile",
    ],
)

py_library(
    name = "platforms",
    srcs = ["platforms.py"],
    deps = [
        ":lib",
        "//pysc2/lib:sc_process",
        "@absl_py//absl/flags",
    ],
)
