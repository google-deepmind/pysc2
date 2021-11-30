load("//pysc2:build_defs.bzl", "pytype_strict_library")

package(default_visibility = ["//visibility:public"])

licenses(["notice"])

cc_library(
    name = "raw_actions",
    srcs = ["raw_actions.cc"],
    hdrs = ["raw_actions.h"],
    deps = [
        "@com_google_absl//absl/container:fixed_array",
        "@s2client_proto//s2clientprotocol:raw_cc_proto",
        "@s2client_proto//s2clientprotocol:sc2api_cc_proto",
    ],
)

cc_library(
    name = "uint8_lookup",
    srcs = ["uint8_lookup.cc"],
    hdrs = ["uint8_lookup.h"],
    deps = [
        "//pysc2/env/converter/cc/game_data/proto:buffs_cc_proto",
        "//pysc2/env/converter/cc/game_data/proto:units_cc_proto",
        "//pysc2/env/converter/cc/game_data/proto:upgrades_cc_proto",
        "@com_google_absl//absl/container:flat_hash_map",
        "@glog",
    ],
)

cc_library(
    name = "visual_actions",
    srcs = ["visual_actions.cc"],
    hdrs = ["visual_actions.h"],
    deps = [
        "@com_google_absl//absl/container:flat_hash_map",
        "@s2client_proto//s2clientprotocol:sc2api_cc_proto",
    ],
)

pytype_strict_library(
    name = "__init__",
    srcs = ["__init__.py"],
)
