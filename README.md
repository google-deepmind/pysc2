# PySC2 - A StarCraft II Machine Learning Environment

PySC2 is DeepMind's python environment wrapper for Blizzard Entertainment's
new [StarCraft II Machine Learning API](https://github.com/deepmind/pysc2).
We have been collaborating with Blizzard to develop StarCraft II into a flexible
environment for RL Research. PySC2 provides an interface for RL agents to
interact with StarCraft 2, getting observations and sending actions.

We have published an accompanying [blogpost](http://deepmind.com/blogpost/XXX)
and [paper](https://arxiv.org/abs/XXX), which outlines our motivation for using
StarCraft II for DeepRL research, and some initial research results using the
environment.

## About

Disclaimer: This is not an official Google product.

If you use the StarCraft II Machine Learning API and/or PySC2 in your research,
please cite the [StarCraft II Paper](https://arxiv.org/abs/XXX)

You can reach us at [pysc2@deepmind.com](mailto:pysc2@deepmind.com).


# Quick Start Guide

## Get PySC2

### PyPI

The easiest way to get PySC2 is to use pip:

```shell
$ pip install pysc2
```

That will install the `pysc2` package along with all the required dependencies.
If you're running on an older system you may need to install `libsdl` libraries
for the `pygame` dependency.

### Git

Alternatively you can install PySC2 with git. First clone the PySC2 repo, then
install the dependencies and `pysc2` package:

```shell
$ git clone https://github.com/deepmind/pysc2.git
$ cd pysc2
pysc2$ pip install .
```

## Get StarCraft II

PySC2 depends on the full StarCraft II game and only works with versions that
include the API, which is 3.16.1 and above.

### Linux

Follow Blizzard's [documentation](https://github.com/Blizzard/s2client-proto) to
get the linux version. By default, PySC2 expects the game to live in
`~/StarCraftII/`. You can override this path by setting the `SC2PATH`
environment variable or creating your own run_config.

### Windows/Mac

Install of the game as normal from [Battle.net](https://battle.net). Even the
[Starter Edition](http://battle.net/sc2/en/legacy-of-the-void/) will work.
If you used the default install location PySC2 should find the latest binary.
If you changed the install location, you'll need to set the `SC2PATH`
environment variable with the correct location.

PySC2 should work on Mac OS and Windows systems running Python 2.7+ or 3.4+,
but has only been thoroughly tested on Linux. We welcome suggestions and patches
for better compatibility with other systems.

## Get the maps

PySC2 has many maps pre-configured, but they need to be downloaded into the SC2
`Maps` directory before they can be played.

Download the [ladder maps](https://blizzard.com/XXX) and the
[mini games](https://github.com/deepmind/pysc2/releases/maps/XXX) and extract
them to your `StarcraftII` directory.

TODO(tewalds): write a download script?

## Run an agent

You can run an agent to test the environment. The UI shows you the actions of
the agent and is helpful for debugging and visualization purposes.

```shell
$ python -m pysc2.bin.agent --map Simple64
```

It runs a random agent by default, but you can specify others if you'd like,
including your own.

```shell
$ pysc2_agent --map CollectMineralShards --agent pysc2.agents.scripted_agent.CollectMineralShards
```

To specify the agent's race, the opponent's difficulty, and more, you can pass
additional flags. Run with `--help` to see what you can change.

## Play the game as a human

There is a human agent interface which is mainly used for debugging, but it can
also be used to play the game. The UI is fairly simple and incomplete, but it's
enough to understand the basics of the game. Also, it runs on Linux.

```shell
$ python -m pysc2.bin.play --map Simple64
or
$ pysc2_play --map Simple64
```

In the UI, hit `?` for a list of the hotkeys. The most basic ones are: `F4` to
quit, `F5` to restart, `F9` to save a replay, and `Pgup`/`Pgdn` to control the
speed of the game. Otherwise use the mouse for selection and keyboard for
commands listed on the left.

The left side is a basic rendering (which will likely be replaced by a proper
rendering some day). The right side is the feature layers that the agent
receives, with some coloring to make it more useful to us.

## Watch a replay

Running the random agent and playing as a human save a replay by default. You
can watch that replay by running:

```shell
$ pysc2_play --replay <path-to-replay>
```

This works for any replay as long as the map can be found by the game.

The same controls work as for playing the game, so `F4` to exit, `pgup`/`pgdn`
to control the speed, etc.

## List the maps

[Maps](docs/maps.md) need to be configured before they're known to the
environment. You can see the list of known maps by running:

```shell
$ python -m pysc2.bin.map_list
```

# Environment Details

A full description of the specifics of how the environment is configured, the
observations and action spaces work is available [here](docs/environment.md).

# Mini-game maps

The mini-game map files referenced in the paper are stored under `pysc2/maps/`.
The maps are configured in the python files. The configs can set player and time
limits, whether to use the game outcome or curriculum score, and a handful of
other things.

For more information about the maps, and how to configure your own, take a
look [here](docs/maps.md).

# Replays

A replay lets you review what happened during a game. You can see the actions
and observations that each player made as they played.

Blizzard is releasing a large number of anonymized 1v1 replays played on the
ladder. You can find instructions for how to get the
[replay files](https://github.com/Blizzard/s2client-api/XXX) on their site. You
can also review your own replays.

Replays can be played back to get the observations and actions made during that
game. The observations are rendered at the resolution you request, so may differ
from what the human actually saw. Similarly the actions specify a point, which
could reflect a different pixel on the human's screen, so may not have an exact
match in our observations, though they should be fairly similar.

Replays are version dependent, so a 3.16 replay will fail in a 3.17 binary.

You can visualize the replays with the full game, or with `pysc2_play`.
Alternatively you can run `pysc2.bin.replay_actions` to process many replays
in parallel.
