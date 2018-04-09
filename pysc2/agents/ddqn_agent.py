from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy

from pysc2.agents import base_agent
from pysc2.lib import actions
from pysc2.lib import features

import keras
from collections import deque
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import Conv2D
from keras.layers import MaxPooling2D
from keras.layers import Flatten

_PLAYER_RELATIVE = features.SCREEN_FEATURES.player_relative.index
_PLAYER_FRIENDLY = 1
_PLAYER_NEUTRAL = 3  # beacon/minerals
_PLAYER_HOSTILE = 4

_NO_OP = actions.FUNCTIONS.no_op.id
_MOVE_SCREEN = actions.FUNCTIONS.Move_screen.id
_ATTACK_SCREEN = actions.FUNCTIONS.Attack_screen.id
_SELECT_ARMY = actions.FUNCTIONS.select_army.id
_NOT_QUEUED = [0]
_SELECT_ALL = [0]

_UNIT_TYPE = features.SCREEN_FEATURES.unit_type.index
_SCREEN_FEATURE = features.SCREEN_FEATURES
_PLAYER_ID = features.SCREEN_FEATURES.player_id.index
_HIT_POINTS = features.SCREEN_FEATURES.unit_hit_points.index
_UNIT_DENSITY_AA = features.SCREEN_FEATURES.unit_density_aa.index

_MAP_LENGTH = 84
_MAP_SIZE = _MAP_LENGTH * _MAP_LENGTH
_FEATURES = [
    _PLAYER_ID,
    _HIT_POINTS,
    _UNIT_DENSITY_AA
]


class DQNAgent:
    def __init__(self):
        self.state_shape = (3, _MAP_LENGTH, _MAP_LENGTH)
        self.output_size = _MAP_SIZE
        self.learning_rate = 0.5
        self.epsilon = 1
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.9
        self.gamma = 0.9
        self.memory = deque(maxlen=2000)
        self.model = self._build_model()

    def _build_model(self):
        # Neural Net for Deep-Q learning Model
        model = Sequential()
        model.add(Conv2D(16, kernel_size=(3, 3), strides=(1, 1), activation='relu', input_shape=self.state_shape))
        model.add(Flatten())
        model.add(Dense(_MAP_SIZE * 8, activation='relu'))
        model.add(Dense(self.output_size, activation='linear'))
        model.compile(loss=keras.losses.categorical_crossentropy,
                      optimizer=keras.optimizers.SGD(lr=0.01),
                      metrics=['accuracy'])
        return model

    def act(self, state):
        if numpy.random.rand() <= self.epsilon:
            return numpy.random.randint(0, self.output_size)
        pred_values = self.model.predict(state)
        return numpy.argmax(pred_values,axis=1)

    def remember(self, state, action, next_state, reward):
        self.memory.append((state, action, next_state, reward))

    def replay(self, batch_size=None):
        if batch_size is None:
            batch_size = int((len(self.memory)) / 10)
        choice = numpy.random.choice(range(len(self.memory)), batch_size)
        minibatch = [self.memory[index] for index in choice]
        for state, action, next_state, reward in minibatch:
            target = (reward + self.gamma *
                      numpy.max(self.model.predict(next_state), axis=1))
            target_f = self.model.predict(state)
            target_f[0][action] = target
            self.model.fit(state, target_f, epochs=1, verbose=0)
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay


class DefeatRoaches(base_agent.BaseAgent):
    """An agent specifically for solving the DefeatRoaches map."""

    def __init__(self):
        super(DefeatRoaches, self).__init__()
        self.agent = DQNAgent()
        self.batch_size = 20
        self.last_action = None
        self.last_state = None

    def step(self, obs):
        super(DefeatRoaches, self).step(obs)

        if _ATTACK_SCREEN in obs.observation["available_actions"]:
            feature = numpy.array([numpy.array([
                obs.observation['feature_screen'][_PLAYER_ID],
                obs.observation['feature_screen'][_HIT_POINTS],
                obs.observation['feature_screen'][_UNIT_DENSITY_AA]
            ])])

            if self.last_action is not None:
                reward = obs.reward
                self.agent.remember([self.last_state], [self.last_action], feature, reward * 500)

            self.last_action = self.agent.act(feature)
            self.last_state = feature

            target = [self.last_action % 84, int(self.last_action / 84)]
            # print("Attack: ", target[0], target[1])
            return actions.FunctionCall(_ATTACK_SCREEN, [_NOT_QUEUED, target])
        elif _SELECT_ARMY in obs.observation["available_actions"]:
            return actions.FunctionCall(_SELECT_ARMY, [_SELECT_ALL])
        else:
            return actions.FunctionCall(_NO_OP, [])

    def reset(self):
        super(DefeatRoaches, self).reset()
        if self.episodes > self.batch_size:
            self.agent.replay(16)
            self.agent.memory.clear()
