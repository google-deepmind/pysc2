workspace(name = "pysc2")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

http_archive(
    name = "bazel_skylib",
    strip_prefix = "bazel-skylib-main",
    urls = ["https://github.com/bazelbuild/bazel-skylib/archive/main.zip"],
)

http_archive(
    name = "rules_python",
    url = "https://github.com/bazelbuild/rules_python/releases/download/0.4.0/rules_python-0.4.0.tar.gz",
    sha256 = "954aa89b491be4a083304a2cb838019c8b8c3720a7abb9c4cb81ac7a24230cea",
)

load("@rules_python//python:pip.bzl", "pip_install")

http_archive(
    name = "rules_cc",
    urls = ["https://github.com/bazelbuild/rules_cc/archive/68cb652a71e7e7e2858c50593e5a9e3b94e5b9a9.zip"],
    strip_prefix = "rules_cc-68cb652a71e7e7e2858c50593e5a9e3b94e5b9a9",
    sha256 = "1e19e9a3bc3d4ee91d7fcad00653485ee6c798efbbf9588d40b34cbfbded143d",
)
load("@rules_cc//cc:repositories.bzl", "rules_cc_dependencies")
rules_cc_dependencies()

# Create a central external repo, @my_deps, that contains Bazel targets for all the
# third-party packages specified in the requirements.txt file.
pip_install(
   name = "my_deps",
   requirements = "@//bazel:requirements.txt",
)

http_archive(
    name = "rules_proto",
    sha256 = "66bfdf8782796239d3875d37e7de19b1d94301e8972b3cbd2446b332429b4df1",
    strip_prefix = "rules_proto-4.0.0",
    urls = [
        "https://mirror.bazel.build/github.com/bazelbuild/rules_proto/archive/refs/tags/4.0.0.tar.gz",
        "https://github.com/bazelbuild/rules_proto/archive/refs/tags/4.0.0.tar.gz",
    ],
)
load("@rules_proto//proto:repositories.bzl", "rules_proto_dependencies", "rules_proto_toolchains")
rules_proto_dependencies()
rules_proto_toolchains()

http_archive(
    name = "com_google_protobuf",
    patches = ["@//bazel:protobuf.patch"],
    urls = ["https://github.com/protocolbuffers/protobuf/archive/refs/tags/v3.19.1.zip"],
    strip_prefix = "protobuf-3.19.1",
)
load("@com_google_protobuf//:protobuf_deps.bzl", "protobuf_deps")
protobuf_deps()

http_archive(
    # It is important that this isn't named simply 'absl' as the project has
    # a subdirectory named that, and Python module lookup fails if we have
    # absl/absl...
    name = "absl_py",
    strip_prefix = "abseil-py-main",
    urls = ["https://github.com/abseil/abseil-py/archive/main.zip"],
)

# Required by absl_py.
http_archive(
    name = "six_archive",
    build_file = "@absl_py//third_party:six.BUILD",
    sha256 = "105f8d68616f8248e24bf0e9372ef04d3cc10104f1980f54d57b2ce73a5ad56a",
    strip_prefix = "six-1.10.0",
    urls = [
        "http://mirror.bazel.build/pypi.python.org/packages/source/s/six/six-1.10.0.tar.gz",
        "https://pypi.python.org/packages/source/s/six/six-1.10.0.tar.gz",
    ],
)

# We can't use the wheels for dm_env and dm_env_rpc because that pulls in
# proto code which leads to incompatibilities with our our protos.
http_archive(
    name = "dm_env_archive",
    build_file = "@//bazel:BUILD.dm_env",
    strip_prefix = "dm_env-3c6844db2aa4ed5994b2c45dbfd9f31ad948fbb8",
    urls = ["https://github.com/deepmind/dm_env/archive/3c6844db2aa4ed5994b2c45dbfd9f31ad948fbb8.zip"],
)

http_archive(
    name = "dm_env_rpc_archive",
    urls = ["https://github.com/deepmind/dm_env_rpc/archive/refs/heads/master.zip"],
    strip_prefix = "dm_env_rpc-master",
    build_file = "@//bazel:BUILD.dm_env_rpc",
)

http_archive(
    name = "s2client_proto",
    urls = ["https://github.com/Blizzard/s2client-proto/archive/refs/heads/master.zip"],
    strip_prefix = "s2client-proto-master",
    patches = ["@//bazel:s2clientprotocol.patch"],
)

http_archive(
    name = "s2protocol",
    urls = ["https://github.com/Blizzard/s2protocol/archive/refs/heads/master.zip"],
    strip_prefix = "s2protocol-master",
    build_file = "@//bazel:BUILD.s2protocol",
)

# C++ dependencies.
http_archive(
    name = "com_google_googletest",
    sha256 = "ff7a82736e158c077e76188232eac77913a15dac0b22508c390ab3f88e6d6d86",
    strip_prefix = "googletest-b6cd405286ed8635ece71c72f118e659f4ade3fb",
    urls = [
        "https://storage.googleapis.com/mirror.tensorflow.org/github.com/google/googletest/archive/b6cd405286ed8635ece71c72f118e659f4ade3fb.zip",
        "https://github.com/google/googletest/archive/b6cd405286ed8635ece71c72f118e659f4ade3fb.zip",
    ],
)

http_archive(
    name = "com_google_googleapis",
    sha256 = "1f742f6cafe616fe73302db010e0b7ee6579cb1ce06010427b7d0995cbd80ce4",
    strip_prefix = "googleapis-6a813acf535e4746fa4a135ce23547bb6425c26d",
    urls = [
        "https://github.com/googleapis/googleapis/archive/6a813acf535e4746fa4a135ce23547bb6425c26d.tar.gz",
    ],
)

load("@com_google_googleapis//:repository_rules.bzl", "switched_rules_by_language")

switched_rules_by_language(
   name = "com_google_googleapis_imports",
   cc = True,
   python = True
)

http_archive(
    name = "com_google_absl",
    sha256 = "35f22ef5cb286f09954b7cc4c85b5a3f6221c9d4df6b8c4a1e9d399555b366ee",  # SHARED_ABSL_SHA
    strip_prefix = "abseil-cpp-997aaf3a28308eba1b9156aa35ab7bca9688e9f6",
    urls = [
        "https://storage.googleapis.com/mirror.tensorflow.org/github.com/abseil/abseil-cpp/archive/997aaf3a28308eba1b9156aa35ab7bca9688e9f6.tar.gz",
        "https://github.com/abseil/abseil-cpp/archive/997aaf3a28308eba1b9156aa35ab7bca9688e9f6.tar.gz",
    ],
)

http_archive(
    name = "pybind11_abseil",
    urls = ["https://github.com/pybind/pybind11_abseil/archive/refs/heads/master.zip"],
    strip_prefix = "pybind11_abseil-master",
)

http_archive(
    name = "pybind11_protobuf",
    urls = ["https://github.com/pybind/pybind11_protobuf/archive/refs/heads/main.zip"],
    strip_prefix = "pybind11_protobuf-main",
)

http_archive(
    name = "pybind11_bazel",
    strip_prefix = "pybind11_bazel-master",
    urls = ["https://github.com/pybind/pybind11_bazel/archive/refs/heads/master.zip"],
)

http_archive(
  name = "pybind11",
  build_file = "@pybind11_bazel//:pybind11.BUILD",
  strip_prefix = "pybind11-2.8.1",
  urls = ["https://github.com/pybind/pybind11/archive/v2.8.1.tar.gz"],
)

load("@pybind11_bazel//:python_configure.bzl", "python_configure")
python_configure(name = "local_config_python")
bind(
    name = "python_headers",
    actual = "@local_config_python//:python_headers",
)

# Required by glog.
http_archive(
    name = "com_github_gflags_gflags",
    sha256 = "34af2f15cf7367513b352bdcd2493ab14ce43692d2dcd9dfc499492966c64dcf",
    strip_prefix = "gflags-2.2.2",
    urls = [
       "https://github.com/gflags/gflags/archive/v2.2.2.tar.gz",
    ],
)

http_archive(
    name = "glog",
    sha256 = "6281aa4eeecb9e932d7091f99872e7b26fa6aacece49c15ce5b14af2b7ec050f",
    urls = [
        "https://github.com/google/glog/archive/96a2f23dca4cc7180821ca5f32e526314395d26a.zip",
    ],
    strip_prefix = "glog-96a2f23dca4cc7180821ca5f32e526314395d26a",
)

http_archive(
    name = "com_github_grpc_grpc",
    patches = ["@//bazel:grpc.patch"],
    strip_prefix = "grpc-master",
    urls = ["https://github.com/grpc/grpc/archive/refs/heads/master.zip"],
)
load("@com_github_grpc_grpc//bazel:grpc_deps.bzl", "grpc_deps")
grpc_deps()
