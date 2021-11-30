load("//pysc2:build_defs.bzl", "pytype_strict_library")

package(default_visibility = ["//visibility:public"])

licenses(["notice"])

filegroup(
    name = "example_actions",
    srcs = glob([
        "actions/*.pbtxt",
    ]),
)

filegroup(
    name = "example_observations",
    srcs = glob([
        "*.pbtxt",
    ]),
)

filegroup(
    name = "example_recordings",
    srcs = glob([
        "recordings/*.pb",
    ]),
)

pytype_strict_library(
    name = "__init__",
    srcs = ["__init__.py"],
)
