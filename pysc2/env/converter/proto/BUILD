load("@com_github_grpc_grpc//bazel:python_rules.bzl", "py_proto_library")

licenses(["notice"])

proto_library(
    name = "converter_proto",
    srcs = ["converter.proto"],
    deps = [
        "@s2client_proto//s2clientprotocol:common_proto",
        "@s2client_proto//s2clientprotocol:sc2api_proto",
    ],
)

py_proto_library(
    name = "converter_py_pb2",
    visibility = ["//visibility:public"],
    deps = [":converter_proto"],
)

cc_proto_library(
    name = "converter_cc_proto",
    visibility = ["//visibility:public"],
    deps = [":converter_proto"],
)
