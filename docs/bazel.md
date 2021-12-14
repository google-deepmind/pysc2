# Building with Bazel

Prior to the inclusion of C++ code it was sufficient to install the
[pip](https://pypi.org/project/pip/) dependencies of PySC2 and to execute the
Python code directly using the Python interpreter. This is still possible if
installing from a [wheel](https://pypi.org/project/wheel/) with a pre-built
distribution matching the platform on which you are running, else when not
referencing any of the C++ code. Where that is not the case, or where you would
like to make changes to the C++ code, a build system becomes necessary. We
support the use of [Bazel](https://bazel.build/), Google's open-source build
tool, for this purpose.

## Supported platforms

We support building with Bazel on Ubuntu Linux with C++ 17. In future we may
support other platforms, should there be demand.

## Example

First of all,
[get Bazel](https://docs.bazel.build/versions/main/install-ubuntu.html). Next,
you may need the Python development environment.

```shell
$ sudo apt update
$ sudo apt install python3 python3-dev python3-venv
```

Build all PySC2 targets (from the workspace root).

```shell
$ bazel build --cxxopt='-std=c++17' ...
```

Run some tests.

```shell
$ bazel test --cxxopt='-std=c++17' pysc2/lib/...
```

Beyond that, everything should be the same as running Python directly as
described in the readme, only rather than using the Python interpreter you use
Bazel to run. For instance...

```shell
$ python -m pysc2.bin.agent --map Simple64
```

becomes...

```shell
$ bazel run --cxxopt='-std=c++17' pysc2/bin:agent -- --map Simple64
```

You may wish to use a [.bazelrc file](https://docs.bazel.build/versions/main/guide.html#bazelrc-the-bazel-configuration-file) to avoid the need to repeatedly specify command-line options, for instance `--cxxopt='-std=c++17'`.
