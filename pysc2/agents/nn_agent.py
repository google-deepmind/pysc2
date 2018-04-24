from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from scipy.stats import multivariate_normal
import numpy

from pysc2.agents import base_agent
from pysc2.lib import actions
from pysc2.lib import features

import os
from os import chdir, listdir
from os.path import isfile, join

import keras
from keras.models import load_model
from collections import deque
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import Conv2D
from keras.layers import MaxPooling2D
from keras.layers import Flatten
from keras.layers import BatchNormalization


MODEL_SAVE_PATH = "model-nn\\"

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
        self.state_shape = (2, 42, 42)
        self.output_size = 42*42
        # self.learning_rate = 0.5
        self.epsilon = 0.0
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.9
        self.gamma = 0.6
        self.memory = deque(maxlen=5000)
        self.start_episode = 0
        self.model = self._build_model()
        self.reward_filter = 0

    def read_file(self):
        onlyfiles = [f for f in listdir(MODEL_SAVE_PATH) if isfile(join(MODEL_SAVE_PATH, f))]
        max_id = 0
        max_filename = ""
        for filename in onlyfiles:
            if filename[-4:] == ".mod":
                end = filename.find('-')
                model_id = 0
                if end == -1:
                    model_id = int(filename[:-4])
                else:
                    model_id = int(filename[:end])
                if model_id > max_id:
                    max_id = model_id
                    max_filename = filename
        if max_id != 0:
            self.start_episode = max_id
            return load_model(MODEL_SAVE_PATH+max_filename)

    def _build_model(self):

        model = self.read_file()

        if model is None:
            # Neural Net for Deep-Q learning Model
            model = Sequential()
            model.add(BatchNormalization(input_shape=self.state_shape))
            model.add(Flatten())
            model.add(Dense(units=84 * 84, activation='relu'))
            model.add(Dense(units=84 * 84, activation='relu'))
            model.add(Dense(units=self.output_size, activation='linear'))
            model.compile(loss=keras.losses.logcosh,
                          optimizer=keras.optimizers.SGD(),
                          metrics=['accuracy'])
        print(model.summary())
        return model

    def act(self, state):
        if numpy.random.rand() <= self.epsilon:
            return numpy.random.randint(0, self.output_size)
        pred_values = self.model.predict(state)
        index = numpy.argmax(pred_values)
        return index

    def remember(self, state, action, next_state, reward):
        if reward == 0 and self.reward_filter != 0:
            self.reward_filter += 1
            self.reward_filter %= 8
            return
        self.memory.append((state, action, next_state, reward))

    def replay(self, batch_size=None):
        if batch_size is None:
            batch_size = int((len(self.memory)) / 10)
        x = []
        y = []
        rad = numpy.random.choice(range(len(self.memory)), batch_size)
        for i in rad:
            state, action, next_state, reward = self.memory[i]
            x.append(state)

            rv = multivariate_normal([int(action%42), int(action/42)], [[2.0, 0.0], [0.0, 2.0]])
            m, n = numpy.mgrid[0:42, 0:42]
            pos = numpy.empty(m.shape + (2,))
            pos[:, :, 0] = m
            pos[:, :, 1] = n
            yy = rv.pdf(pos) * reward
            yy = yy.flatten()
            r = numpy.max(self.model.predict(numpy.array([next_state])))
            yy += r * self.gamma
            y.append(yy)

        x = numpy.array(x)
        y = numpy.array(y)
        self.model.fit(x, y, epochs=1, verbose=0)
        # x = []
        # y = []

        # self.memory.clear()
        return


class DefeatRoaches(base_agent.BaseAgent):
    """An agent specifically for solving the DefeatRoaches map."""

    def __init__(self):
        super(DefeatRoaches, self).__init__()
        self.agent = DQNAgent()
        self.start_episode = 20
        self.last_action = None
        self.last_state = None
        self.step_filter = 0
        self.step_reward = 0
        self.first_step = False
        self.score = 0
        self.episodes = self.agent.start_episode
        self.max_score = -9
        self.min_score = 500

    def step(self, obs):
        super(DefeatRoaches, self).step(obs)

        self.step_reward += obs.reward

        self.step_filter += 1
        self.step_filter %= 20
        if self.step_filter != 0:
            return actions.FunctionCall(_NO_OP, [])

        if _ATTACK_SCREEN in obs.observation["available_actions"]:
            player_relative = obs.observation.feature_screen.player_relative
            roaches = self.downscale(1*numpy.array(player_relative == _PLAYER_ENEMY))
            marines = self.downscale(1*numpy.array(player_relative == _PLAYER_SELF))
            hitpoint = numpy.array(obs.observation['feature_screen'][_HIT_POINTS])
            unitdensity = numpy.array(obs.observation['feature_screen'][_UNIT_DENSITY_AA])
            feature = numpy.array([
                roaches,
                marines,
                # hitpoint,
                # unitdensity
            ])

            if self.first_step and self.episodes < 200:
                y = roaches*20 + marines * -5 - 5
                self.agent.model.fit(numpy.array([feature]), numpy.array([y.flatten()]), epochs=200, verbose=0)
                self.first_step = False

            if self.last_action is not None:
                self.agent.remember(self.last_state, self.last_action, feature, self.step_reward)
                self.step_reward = 0
                self.agent.replay(10)

            self.last_action = self.agent.act(numpy.array([feature]))
            self.last_state = feature

            target = [int(self.last_action % 42) * 2 + 1, int(self.last_action / 42) * 2 + 1]
            # print("action:", self.last_action,"Attack: ", target[0], target[1])

            self.step_reward = 0
            return actions.FunctionCall(_ATTACK_SCREEN, [_NOT_QUEUED, target])
        elif _SELECT_ARMY in obs.observation["available_actions"]:
            return actions.FunctionCall(_SELECT_ARMY, [_SELECT_ALL])
        else:
            return actions.FunctionCall(_NO_OP, [])

    def reset(self):
        super(DefeatRoaches, self).reset()
        print("eplison:", self.agent.epsilon)
        self.first_step = True
        if self.agent.epsilon > self.agent.epsilon_min:
            self.agent.epsilon *= self.agent.epsilon_decay

        self.score += self.reward
        if self.reward > self.max_score:
            self.max_score = self.reward
        if self.reward < self.min_score:
            self.min_score = self.reward

        self.reward = 0

        if self.episodes != 0 and self.episodes % 100 == 0:
            self.agent.model.save(MODEL_SAVE_PATH + str(self.episodes) + "-" + str(self.score / 100)
                                  + "-max" + str(self.max_score) + "-min" + str(self.min_score) + ".mod")
            print("============================\nepisode", self.episodes - 50, "-", self.episodes, "score", self.score / 100
                  , "-max", str(self.max_score), "-min" + str(self.min_score))
            self.score = 0
            self.max_score = -9
            self.min_score = 500

    def downscale(self, feature):
        m, n = feature.shape
        l = 2
        res = numpy.empty([int(m/l), int(n/l)])
        for i in range(int(m/l)):
            for j in range(int(n/l)):
                res[i, j] = numpy.max(feature[i*l:i*l+l, j*l:j*l+l])
        return res
