workspace(name = "pysc2")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("@bazel_tools//tools/build_defs/repo:git.bzl", "git_repository", "new_git_repository")

http_archive(
    name = "rules_python",
    url = "https://github.com/bazelbuild/rules_python/releases/download/0.4.0/rules_python-0.4.0.tar.gz",
    sha256 = "954aa89b491be4a083304a2cb838019c8b8c3720a7abb9c4cb81ac7a24230cea",
)

load("@rules_python//python:pip.bzl", "pip_install")

# Create a central external repo, @my_deps, that contains Bazel targets for all the
# third-party packages specified in the requirements.txt file.
pip_install(
   name = "my_deps",
   requirements = "requirements.txt",
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

git_repository(
    name = "com_google_protobuf",
    remote = "https://github.com/protocolbuffers/protobuf",
    commit = "6d4e7fd7966c989e38024a8ea693db83758944f1",
    shallow_since = "1570061847 -0700",
)
load("@com_google_protobuf//:protobuf_deps.bzl", "protobuf_deps")
protobuf_deps()

http_archive(
    # It is important that this isn't named simply 'absl' as the project has
    # a subdirectory named that, and Python module lookup fails if we have
    # absl/absl...
    name = "absl_py",
    strip_prefix = "abseil-py-master",
    urls = ["https://github.com/abseil/abseil-py/archive/master.zip"],
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

new_git_repository(
  name = "s2client_proto",
  remote = "https://github.com/Blizzard/s2client-proto.git",
  commit = "3a11b32271384eb4913a8b294d58fa5d560e3426",
  shallow_since = "1634587790 +0000",
  build_file = "BUILD.s2clientprotocol",
)

new_git_repository(
  name = "s2protocol",
  remote = "https://github.com/Blizzard/s2protocol.git",
  commit = "4bfe857bb832eee12cc6307dd699e3b74bd7e1b2",
  shallow_since = "1634750077 +0000",
  build_file = "BUILD.s2protocol",
)

# Protobuf expects an //external:python_headers label which would contain the
# Python headers if fast Python protos is enabled. Since we are not using fast
# Python protos, bind python_headers to a dummy target.
bind(
    name = "python_headers",
    actual = "//pysc2:dummy",
)
