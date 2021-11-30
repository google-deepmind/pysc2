load("//pysc2:build_defs.bzl", "pytype_library")

package(default_visibility = ["//visibility:public"])

licenses(["notice"])  # Apache2 license

filegroup(
    name = "map_files",
    srcs = glob([
        "**/*.SC2Map",
    ]),
)

pytype_library(
    name = "maps",
    srcs = [
        "__init__.py",
        "ladder.py",
        "lib.py",
        "melee.py",
        "mini_games.py",
    ],
    data = [":map_files"],
    srcs_version = "PY3",
    deps = [
        "@absl_py//absl/logging",
    ],
)
