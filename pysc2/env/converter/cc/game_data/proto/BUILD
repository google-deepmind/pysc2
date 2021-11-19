load("@com_github_grpc_grpc//bazel:python_rules.bzl", "py_proto_library")

licenses(["notice"])

proto_library(
    name = "buffs_proto",
    srcs = ["buffs.proto"],
)

cc_proto_library(
    name = "buffs_cc_proto",
    visibility = ["//visibility:public"],
    deps = [":buffs_proto"],
)

py_proto_library(
    name = "buffs_py_pb2",
    visibility = ["//visibility:public"],
    deps = [":buffs_proto"],
)

proto_library(
    name = "units_proto",
    srcs = ["units.proto"],
)

cc_proto_library(
    name = "units_cc_proto",
    visibility = ["//visibility:public"],
    deps = [":units_proto"],
)

py_proto_library(
    name = "units_py_pb2",
    visibility = ["//visibility:public"],
    deps = [":units_proto"],
)

proto_library(
    name = "upgrades_proto",
    srcs = ["upgrades.proto"],
)

cc_proto_library(
    name = "upgrades_cc_proto",
    visibility = ["//visibility:public"],
    deps = [":upgrades_proto"],
)

py_proto_library(
    name = "upgrades_py_pb2",
    visibility = ["//visibility:public"],
    deps = [":upgrades_proto"],
)
