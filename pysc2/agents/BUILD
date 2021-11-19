load("@my_deps//:requirements.bzl", "requirement")

package(default_visibility = ["//visibility:public"])

licenses(["notice"])  # Apache2 license

py_library(
    name = "agents",
    srcs_version = "PY3",
    deps = [
        ":base_agent",
        ":random_agent",
        ":scripted_agent",
    ],
)

py_library(
    name = "base_agent",
    srcs = ["base_agent.py"],
    srcs_version = "PY3",
    deps = [
        "//pysc2/lib:actions",
    ],
)

py_library(
    name = "no_op_agent",
    srcs = ["no_op_agent.py"],
    deps = [
        ":base_agent",
        "@s2client_proto//s2clientprotocol:sc2api_py_pb2",
    ],
)

py_library(
    name = "scripted_agent",
    srcs = ["scripted_agent.py"],
    srcs_version = "PY3",
    deps = [
        ":base_agent",
        requirement("numpy"),
        "//pysc2/lib:actions",
        "//pysc2/lib:features",
    ],
)

py_library(
    name = "random_agent",
    srcs = ["random_agent.py"],
    srcs_version = "PY3",
    deps = [
        ":base_agent",
        requirement("numpy"),
        "//pysc2/lib:actions",
    ],
)
