# DQN agent for DefeatRoaches
#### Sicheng Wang(wang.sich@husky.neu.edu)

This is a DQN agent for DefeatRoaches mini-game based on [PySC2](https://github.com/deepmind/pysc2).
The agent has two versions:\
    1. Simple neural network agent\
    2. Convolutional neural network agent\
Both agents are implemented with [Keras](https://keras.io/).

# Quick Start Guide
## Environment

StarCraft2 and dependencies for PySC2is required.
TensorFlow and Keras is required.

## Run an agent

To run NN agent:

```shell
$ python -m pysc2.bin.agent --map DefeatRoaches --agent pysc2.agents.nn_agent.DefeatRoaches --max_agent_steps 0
```

To run CNN agent:

```shell
$ python -m pysc2.bin.agent --map DefeatRoaches --agent pysc2.agents.cnn_agent.DefeatRoaches --max_agent_steps 0
```

Models are saved every 100 episodes, marked with their average score, max score and min score.
The training will continue from where it stopped the last time.
