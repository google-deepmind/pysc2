load("//pysc2:build_defs.bzl", "pytype_strict_library")

package(default_visibility = ["//visibility:public"])

licenses(["notice"])

cc_library(
    name = "castops",
    hdrs = ["castops.h"],
)

cc_library(
    name = "check_protos_equal",
    hdrs = ["check_protos_equal.h"],
    deps = [
        "@com_google_absl//absl/status",
        "@com_google_protobuf//:protobuf",
    ],
)

cc_library(
    name = "convert_obs",
    srcs = ["convert_obs.cc"],
    hdrs = ["convert_obs.h"],
    deps = [
        ":castops",
        ":encode_image_data",
        ":general_order_ids",
        ":map_util",
        ":raw_actions_encoder",
        ":raw_camera",
        ":tensor_util",
        "//pysc2/env/converter/cc/game_data:uint8_lookup",
        "@com_google_absl//absl/container:flat_hash_map",
        "@com_google_absl//absl/container:flat_hash_set",
        "@dm_env_rpc_archive//:dm_env_rpc_cc_proto",
        "@com_google_protobuf//:protobuf_lite",
        "@glog",
        "@s2client_proto//s2clientprotocol:common_cc_proto",
        "@s2client_proto//s2clientprotocol:raw_cc_proto",
        "@s2client_proto//s2clientprotocol:sc2api_cc_proto",
    ],
)

cc_test(
    name = "convert_obs_test",
    srcs = ["convert_obs_test.cc"],
    data = [
        "//pysc2/env/converter/cc/test_data:example_recordings",
    ],
    deps = [
        ":convert_obs",
        ":file_util",
        ":map_util",
        ":tensor_util",
        "//pysc2/env/converter/cc/game_data/proto:units_cc_proto",
        "//pysc2/env/converter/proto:converter_cc_proto",
        "@com_google_absl//absl/container:flat_hash_set",
        "@com_google_absl//absl/status",
        "@com_google_googletest//:gtest_main",
        "@s2client_proto//s2clientprotocol:spatial_cc_proto",
    ],
)

cc_library(
    name = "converter",
    srcs = ["converter.cc"],
    hdrs = ["converter.h"],
    deps = [
        ":convert_obs",
        ":features",
        ":raw_actions_encoder",
        ":raw_converter",
        ":tensor_util",
        ":unit_lookups",
        ":visual_converter",
        "//pysc2/env/converter/proto:converter_cc_proto",
        "@com_google_absl//absl/container:flat_hash_map",
        "@com_google_absl//absl/status",
        "@com_google_absl//absl/status:statusor",
        "@dm_env_rpc_archive//:dm_env_rpc_cc_proto",
        "@glog",
        "@s2client_proto//s2clientprotocol:common_cc_proto",
        "@s2client_proto//s2clientprotocol:sc2api_cc_proto",
        "@s2client_proto//s2clientprotocol:spatial_cc_proto",
    ],
)

cc_test(
    name = "converter_test",
    srcs = ["converter_test.cc"],
    deps = [
        ":check_protos_equal",
        ":converter",
        "//pysc2/env/converter/cc/game_data:raw_actions",
        "//pysc2/env/converter/proto:converter_cc_proto",
        "@com_google_absl//absl/container:flat_hash_map",
        "@com_google_absl//absl/status",
        "@com_google_absl//absl/strings",
        "@dm_env_rpc_archive//:dm_env_rpc_cc_proto",
        "@com_google_googletest//:gtest_main",
        "@glog",
        "@s2client_proto//s2clientprotocol:common_cc_proto",
        "@s2client_proto//s2clientprotocol:sc2api_cc_proto",
        "@s2client_proto//s2clientprotocol:spatial_cc_proto",
    ],
)

cc_library(
    name = "encode_image_data",
    hdrs = ["encode_image_data.h"],
    deps = [
        ":tensor_util",
        "@dm_env_rpc_archive//:dm_env_rpc_cc_proto",
        "@glog",
        "@s2client_proto//s2clientprotocol:common_cc_proto",
    ],
)

cc_library(
    name = "features",
    srcs = ["features.cc"],
    hdrs = ["features.h"],
    deps = [
        "//pysc2/env/converter/cc/game_data:uint8_lookup",
        "@com_google_absl//absl/container:flat_hash_map",
        "@com_google_absl//absl/status",
        "@com_google_absl//absl/status:statusor",
        "@com_google_absl//absl/strings",
    ],
)

cc_library(
    name = "file_util",
    srcs = ["file_util.cc"],
    hdrs = ["file_util.h"],
    deps = [
        "@com_google_absl//absl/status",
        "@com_google_absl//absl/strings",
        "@com_google_protobuf//:protobuf",
        "@com_google_protobuf//:protobuf_lite",
    ],
)

cc_library(
    name = "general_order_ids",
    srcs = ["general_order_ids.cc"],
    hdrs = ["general_order_ids.h"],
    deps = [
        ":tensor_util",
        "//pysc2/env/converter/cc/game_data:raw_actions",
        "@com_google_absl//absl/container:flat_hash_map",
        "@dm_env_rpc_archive//:dm_env_rpc_cc_proto",
    ],
)

cc_library(
    name = "map_util",
    srcs = ["map_util.cc"],
    hdrs = ["map_util.h"],
    deps = [
        ":castops",
        "@s2client_proto//s2clientprotocol:common_cc_proto",
    ],
)

cc_library(
    name = "raw_actions_encoder",
    srcs = ["raw_actions_encoder.cc"],
    hdrs = ["raw_actions_encoder.h"],
    deps = [
        ":tensor_util",
        "//pysc2/env/converter/cc/game_data:raw_actions",
        "@com_google_absl//absl/container:fixed_array",
        "@com_google_absl//absl/container:flat_hash_map",
        "@com_google_absl//absl/container:flat_hash_set",
        "@com_google_absl//absl/random",
        "@com_google_absl//absl/status",
        "@com_google_absl//absl/status:statusor",
        "@com_google_absl//absl/strings",
        "@dm_env_rpc_archive//:dm_env_rpc_cc_proto",
        "@glog",
        "@s2client_proto//s2clientprotocol:common_cc_proto",
        "@s2client_proto//s2clientprotocol:raw_cc_proto",
        "@s2client_proto//s2clientprotocol:sc2api_cc_proto",
    ],
)

cc_test(
    name = "raw_actions_encoder_test",
    srcs = ["raw_actions_encoder_test.cc"],
    data = [
        "//pysc2/env/converter/cc/test_data:example_observations",
    ],
    deps = [
        ":file_util",
        ":map_util",
        ":raw_actions_encoder",
        "//pysc2/env/converter/cc/game_data:raw_actions",
        "@com_google_absl//absl/container:flat_hash_map",
        "@com_google_absl//absl/status",
        "@com_google_absl//absl/strings",
        "@com_google_googletest//:gtest_main",
        "@com_google_protobuf//:protobuf",
        "@glog",
        "@s2client_proto//s2clientprotocol:sc2api_cc_proto",
    ],
)

cc_library(
    name = "raw_camera",
    srcs = ["raw_camera.cc"],
    hdrs = ["raw_camera.h"],
    deps = [
        ":map_util",
        "@dm_env_rpc_archive//:dm_env_rpc_cc_proto",
        "@glog",
        "@s2client_proto//s2clientprotocol:common_cc_proto",
    ],
)

cc_library(
    name = "raw_converter",
    srcs = ["raw_converter.cc"],
    hdrs = ["raw_converter.h"],
    deps = [
        ":convert_obs",
        ":general_order_ids",
        ":map_util",
        ":raw_actions_encoder",
        ":raw_camera",
        ":tensor_util",
        "//pysc2/env/converter/cc/game_data:uint8_lookup",
        "//pysc2/env/converter/proto:converter_cc_proto",
        "@com_google_absl//absl/container:flat_hash_map",
        "@com_google_absl//absl/container:flat_hash_set",
        "@com_google_absl//absl/status",
        "@com_google_absl//absl/status:statusor",
        "@com_google_absl//absl/strings",
        "@dm_env_rpc_archive//:dm_env_rpc_cc_proto",
        "@s2client_proto//s2clientprotocol:common_cc_proto",
        "@s2client_proto//s2clientprotocol:sc2api_cc_proto",
    ],
)

cc_library(
    name = "tensor_util",
    srcs = ["tensor_util.cc"],
    hdrs = ["tensor_util.h"],
    deps = [
        "@com_google_absl//absl/strings",
        "@dm_env_rpc_archive//:dm_env_rpc_cc_proto",
        "@com_google_protobuf//:protobuf_lite",
        "@glog",
    ],
)

cc_library(
    name = "unit_lookups",
    srcs = ["unit_lookups.cc"],
    hdrs = ["unit_lookups.h"],
    deps = [
        "//pysc2/env/converter/cc/game_data/proto:units_cc_proto",
        "@com_google_absl//absl/container:flat_hash_map",
        "@glog",
        "@s2client_proto//s2clientprotocol:common_cc_proto",
    ],
)

cc_test(
    name = "unit_lookups_test",
    srcs = ["unit_lookups_test.cc"],
    deps = [
        ":unit_lookups",
        "//pysc2/env/converter/cc/game_data/proto:units_cc_proto",
        "@com_google_googletest//:gtest_main",
    ],
)

cc_library(
    name = "visual_actions",
    srcs = ["visual_actions.cc"],
    hdrs = ["visual_actions.h"],
    deps = [
        ":tensor_util",
        "//pysc2/env/converter/cc/game_data:visual_actions",
        "@com_google_absl//absl/container:flat_hash_map",
        "@com_google_absl//absl/strings",
        "@dm_env_rpc_archive//:dm_env_rpc_cc_proto",
        "@glog",
        "@s2client_proto//s2clientprotocol:common_cc_proto",
        "@s2client_proto//s2clientprotocol:sc2api_cc_proto",
        "@s2client_proto//s2clientprotocol:spatial_cc_proto",
        "@s2client_proto//s2clientprotocol:ui_cc_proto",
    ],
)

cc_test(
    name = "visual_actions_test",
    srcs = ["visual_actions_test.cc"],
    data = [
        "//pysc2/env/converter/cc/test_data:example_actions",
    ],
    deps = [
        ":check_protos_equal",
        ":file_util",
        ":tensor_util",
        ":visual_actions",
        "@com_google_absl//absl/status",
        "@com_google_googletest//:gtest_main",
        "@s2client_proto//s2clientprotocol:sc2api_cc_proto",
    ],
)

cc_library(
    name = "visual_converter",
    srcs = ["visual_converter.cc"],
    hdrs = ["visual_converter.h"],
    deps = [
        ":convert_obs",
        ":features",
        ":tensor_util",
        ":visual_actions",
        "//pysc2/env/converter/proto:converter_cc_proto",
        "@com_google_absl//absl/container:flat_hash_map",
        "@com_google_absl//absl/container:flat_hash_set",
        "@com_google_absl//absl/status",
        "@com_google_absl//absl/status:statusor",
        "@com_google_absl//absl/strings",
        "@dm_env_rpc_archive//:dm_env_rpc_cc_proto",
        "@s2client_proto//s2clientprotocol:common_cc_proto",
        "@s2client_proto//s2clientprotocol:sc2api_cc_proto",
        "@s2client_proto//s2clientprotocol:spatial_cc_proto",
        "@s2client_proto//s2clientprotocol:ui_cc_proto",
    ],
)

cc_test(
    name = "visual_converter_test",
    srcs = ["visual_converter_test.cc"],
    deps = [
        ":check_protos_equal",
        ":features",
        ":tensor_util",
        ":visual_converter",
        "//pysc2/env/converter/proto:converter_cc_proto",
        "@com_google_absl//absl/status",
        "@dm_env_rpc_archive//:dm_env_rpc_cc_proto",
        "@com_google_googletest//:gtest_main",
        "@s2client_proto//s2clientprotocol:common_cc_proto",
        "@s2client_proto//s2clientprotocol:spatial_cc_proto",
    ],
)

pytype_strict_library(
    name = "__init__",
    srcs = ["__init__.py"],
)
