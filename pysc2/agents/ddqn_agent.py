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
_PLAYER_SELF = features.PlayerRelative.SELF
_PLAYER_NEUTRAL = features.PlayerRelative.NEUTRAL  # beacon/minerals
_PLAYER_ENEMY = features.PlayerRelative.ENEMY

_MAP_LENGTH = 84
_MAP_SIZE = _MAP_LENGTH * _MAP_LENGTH
_FEATURES = [
    _PLAYER_ID,
    _HIT_POINTS,
    _UNIT_DENSITY_AA
]


class DQNAgent:
    def __init__(self):
        self.state_shape = (4, _MAP_LENGTH, _MAP_LENGTH)
        self.output_size = _MAP_SIZE
        self.learning_rate = 0.5
        self.epsilon = 0.9
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.98
        self.gamma = 0.2
        self.living_expense = 0.1
        self.memory = deque(maxlen=5000)
        self.model = self._build_model()
        self.reward_filter = 0

    def _build_model(self):
        # Neural Net for Deep-Q learning Model
        model = Sequential()
        model.add(Conv2D(16, kernel_size=(4, 4), strides=(2, 2), activation='relu', input_shape=self.state_shape, data_format="channels_first"))
        model.add(MaxPooling2D(pool_size=(2, 2), strides=None, data_format='channels_first'))
        model.add(Conv2D(64, kernel_size=(4, 4), strides=(2, 2), activation='relu', data_format='channels_first'))
        model.add(MaxPooling2D(pool_size=(2, 2), strides=None, data_format='channels_first'))
        model.add(Flatten())
        model.add(Dense(_MAP_SIZE * 8, activation='relu'))
        model.add(Dense(self.output_size, activation='linear'))
        model.compile(loss=keras.losses.categorical_crossentropy,
                      optimizer=keras.optimizers.Adam(lr=0.01),
                      metrics=['accuracy'])
        return model

    def act(self, state):
        if numpy.random.rand() <= self.epsilon:
            return numpy.random.randint(0, self.output_size)
        pred_values = self.model.predict(state)
        # if numpy.argmax(pred_values) == 0:
        #     print("pred0")
        # else:
        #     print("pred1")
        return numpy.argmax(pred_values)

    def remember(self, state, action, next_state, reward):
        if reward == 0 and self.reward_filter != 0:
            self.reward_filter += 1
            self.reward_filter %= 8
            return
        self.memory.append((state, action, next_state, reward))

    def replay(self, batch_size=None):
        if batch_size is None:
            batch_size = int((len(self.memory)) / 10)
        choice = numpy.random.choice(range(len(self.memory)), batch_size)
        minibatch = [self.memory[index] for index in choice]
        history = None
        for state, action, next_state, reward in minibatch:
            target = (reward - self.living_expense + self.gamma *
                      numpy.max(self.model.predict(next_state)))
            target_f = self.model.predict(state)
            target_f[0][action] = target
            history = self.model.fit(state, target_f, epochs=1, verbose=0)
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        return history


class DefeatRoaches(base_agent.BaseAgent):
    """An agent specifically for solving the DefeatRoaches map."""

    def __init__(self):
        super(DefeatRoaches, self).__init__()
        self.agent = DQNAgent()
        self.batch_size = 10
        self.last_action = None
        self.last_state = None
        self.step_filter = 0

    def step(self, obs):
        super(DefeatRoaches, self).step(obs)
        if self.step_filter != 0:
            self.step_filter += 1
            self.step_filter %= 10
            return actions.FunctionCall(_NO_OP, [])
        if _ATTACK_SCREEN in obs.observation["available_actions"]:
            player_relative = obs.observation.feature_screen.player_relative
            roaches = player_relative == _PLAYER_ENEMY
            marines = player_relative == _PLAYER_SELF
            feature = numpy.array([numpy.array([
                roaches,
                marines,
                obs.observation['feature_screen'][_HIT_POINTS],
                obs.observation['feature_screen'][_UNIT_DENSITY_AA]
            ])])

            if self.last_action is not None:
                reward = obs.reward - self.agent.living_expense
                self.agent.remember(self.last_state, self.last_action, feature, reward)

            self.last_action = self.agent.act(feature)
            self.last_state = feature

            target = [self.last_action % 84, int(self.last_action / 84)]
            # print("action:", self.last_action,"Attack: ", target[0], target[1])
            return actions.FunctionCall(_ATTACK_SCREEN, [_NOT_QUEUED, target])
        elif _SELECT_ARMY in obs.observation["available_actions"]:
            return actions.FunctionCall(_SELECT_ARMY, [_SELECT_ALL])
        else:
            return actions.FunctionCall(_NO_OP, [])

    def reset(self):
        super(DefeatRoaches, self).reset()
        if self.episodes > self.batch_size:
            hitory = self.agent.replay(8)
            print("loss:", hitory.history['loss'], "eplison:", self.agent.epsilon)
