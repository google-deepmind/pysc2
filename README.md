<div align="center">
  <a href="https://www.youtube.com/watch?v=-fKUyT14G-8"
     target="_blank">
    <img src="http://img.youtube.com/vi/-fKUyT14G-8/0.jpg"
         alt="DeepMind open source PySC2 toolset for Starcraft II"
         width="240" height="180" border="10" />
  </a>
  <a href="https://www.youtube.com/watch?v=6L448yg0Sm0"
     target="_blank">
    <img src="http://img.youtube.com/vi/6L448yg0Sm0/0.jpg"
         alt="StarCraft II 'mini games' for AI research"
         width="240" height="180" border="10" />
  </a>
  <a href="https://www.youtube.com/watch?v=WEOzide5XFc"
     target="_blank">
    <img src="http://img.youtube.com/vi/WEOzide5XFc/0.jpg"
         alt="Trained and untrained agents play StarCraft II 'mini-game'"
         width="240" height="180" border="10" />
  </a>
</div>

# PySC2 - StarCraft II Learning Environment

[PySC2](https://github.com/deepmind/pysc2) is [DeepMind](http://deepmind.com)'s
Python component of the StarCraft II Learning Environment (SC2LE). It exposes
[Blizzard Entertainment](http://blizzard.com)'s [StarCraft II Machine Learning
API](https://github.com/Blizzard/s2client-proto) as a Python RL Environment.
This is a collaboration between DeepMind and Blizzard to develop StarCraft II
into a rich environment for RL research. PySC2 provides an interface for RL
agents to interact with StarCraft 2, getting observations and sending actions.


We have published an accompanying
[blogpost](https://deepmind.com/blog/deepmind-and-blizzard-open-starcraft-ii-ai-research-environment/)
and [paper](https://arxiv.org/abs/1708.04782), which outlines our
motivation for using StarCraft II for DeepRL research, and some initial research
results using the environment.

## About

Disclaimer: This is not an official Google product.

If you use the StarCraft II Machine Learning API and/or PySC2 in your research,
please cite the [StarCraft II Paper](https://arxiv.org/abs/1708.04782)

You can reach us at [pysc2@deepmind.com](mailto:pysc2@deepmind.com).


# Quick Start Guide

## Get PySC2

### PyPI

The easiest way to get PySC2 is to use pip:

```shell
$ pip install pysc2
```

That will install the `pysc2` package along with all the required dependencies.
[virtualenv](https://pypi.python.org/pypi/virtualenv) can help manage your
dependencies. You may also need to upgrade pip: `pip install --upgrade pip`
for the `pysc2` install to work. If you're running on an older system you may
need to install `libsdl` libraries for the `pygame` dependency.

Pip will install a few of the  binaries to your bin directory. `pysc2_play` can
be used as a shortcut to `python -m pysc2.bin.play`.

### Git

Alternatively you can install PySC2 with git. First clone the PySC2 repo, then
install the dependencies and `pysc2` package:

```shell
$ git clone https://github.com/deepmind/pysc2.git
$ pip install pysc2/
```

## Get StarCraft II

PySC2 depends on the full StarCraft II game and only works with versions that
include the API, which is 3.16.1 and above.

### Linux

Follow Blizzard's [documentation](https://github.com/Blizzard/s2client-proto#downloads) to
get the linux version. By default, PySC2 expects the game to live in
`~/StarCraftII/`. You can override this path by setting the `SC2PATH`
environment variable or creating your own run_config.

### Windows/MacOS

Install of the game as normal from [Battle.net](https://battle.net). Even the
[Starter Edition](http://battle.net/sc2/en/legacy-of-the-void/) will work.
If you used the default install location PySC2 should find the latest binary.
If you changed the install location, you might need to set the `SC2PATH`
environment variable with the correct location.

PySC2 should work on MacOS and Windows systems running Python 2.7+ or 3.4+,
but has only been thoroughly tested on Linux. We welcome suggestions and patches
for better compatibility with other systems.

## Get the maps

PySC2 has many maps pre-configured, but they need to be downloaded into the SC2
`Maps` directory before they can be played.

Download the [ladder maps](https://github.com/Blizzard/s2client-proto#downloads)
and the [mini games](https://github.com/deepmind/pysc2/releases/download/v1.2/mini_games.zip)
and extract them to your `StarcraftII/Maps/` directory.

## Run an agent

You can run an agent to test the environment. The UI shows you the actions of
the agent and is helpful for debugging and visualization purposes.

```shell
$ python -m pysc2.bin.agent --map Simple64
```

It runs a random agent by default, but you can specify others if you'd like,
including your own.

```shell
$ python -m pysc2.bin.agent --map CollectMineralShards --agent pysc2.agents.scripted_agent.CollectMineralShards
```

You can also run two agents against each other.

```shell
$ python -m pysc2.bin.agent --map Simple64 --agent2 pysc2.agents.random_agent.RandomAgent
```

To specify the agent's race, the opponent's difficulty, and more, you can pass
additional flags. Run with `--help` to see what you can change.

## Play the game as a human

There is a human agent interface which is mainly used for debugging, but it can
also be used to play the game. The UI is fairly simple and incomplete, but it's
enough to understand the basics of the game. Also, it runs on Linux.

```shell
$ python -m pysc2.bin.play --map Simple64
```

In the UI, hit `?` for a list of the hotkeys. The most basic ones are: `F4` to
quit, `F5` to restart, `F9` to save a replay, and `Pgup`/`Pgdn` to control the
speed of the game. Otherwise use the mouse for selection and keyboard for
commands listed on the left.

The left side is a basic rendering. The right side is the feature layers that
the agent receives, with some coloring to make it more useful to us. You can
enable or disable RGB or feature layer rendering and their resolutions with
command-line flags.

## Watch a replay

Running an agent and playing as a human save a replay by default. You can watch
that replay by running:

```shell
$ python -m pysc2.bin.play --replay <path-to-replay>
```

This works for any replay as long as the map can be found by the game.

The same controls work as for playing the game, so `F4` to exit, `pgup`/`pgdn`
to control the speed, etc.

You can save a video of the replay with the `--video` flag.

## List the maps

[Maps](docs/maps.md) need to be configured before they're known to the
environment. You can see the list of known maps by running:

```shell
$ python -m pysc2.bin.map_list
```

## Run the tests

If you want to submit a pull request, please make sure the tests pass on both
python 2 and 3.

```shell
$ python -m pysc2.bin.run_tests
```

# Environment Details

For a full description of the specifics of how the environment is configured,
the observations and action spaces work read the
[environment documentation](docs/environment.md).

# Mini-game maps

The mini-game map files referenced in the paper are stored under `pysc2/maps/`
but must be installed in `$SC2PATH/Maps`. Make sure to follow the download
instructions above.

Maps are configured in the Python files in `pysc2/maps/`. The configs can set
player and time limits, whether to use the game outcome or curriculum score, and
a handful of other things. For more information about the maps, and how to
configure your own, read the [maps documentation](docs/maps.md).

# Replays

A replay lets you review what happened during a game. You can see the actions
and observations that each player made as they played.

Blizzard is releasing a large number of anonymized 1v1 replays played on the
ladder. You can find instructions for how to get the
[replay files](https://github.com/Blizzard/s2client-proto#downloads) on their
site. You can also review your own replays.

Replays can be played back to get the observations and actions made during that
game. The observations are rendered at the resolution you request, so may differ
from what the human actually saw. Similarly the actions specify a point, which
could reflect a different pixel on the human's screen, so may not have an exact
match in our observations, though they should be fairly similar.

Replays are version dependent, so a 3.16 replay will fail in a 3.16.1 or 3.17
binary.

You can visualize the replays with the full game, or with `pysc2.bin.play`.
Alternatively you can run `pysc2.bin.replay_actions` to process many replays
in parallel.
