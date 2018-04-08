
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy

from pysc2.agents import base_agent
from pysc2.lib import actions
from pysc2.lib import features

from collections import deque
from keras.models import Sequential
from keras.layers import Dense
from keras.optimizers import Adam


_PLAYER_RELATIVE = features.SCREEN_FEATURES.player_relative.index
_PLAYER_FRIENDLY = 1
_PLAYER_NEUTRAL = 3  # beacon/minerals
_PLAYER_HOSTILE = 4
_UNIT_TYPE = features.SCREEN_FEATURES.unit_type.index

_NO_OP = actions.FUNCTIONS.no_op.id
_MOVE_SCREEN = actions.FUNCTIONS.Move_screen.id
_ATTACK_SCREEN = actions.FUNCTIONS.Attack_screen.id
_SELECT_ARMY = actions.FUNCTIONS.select_army.id
_NOT_QUEUED = [0]
_SELECT_ALL = [0]

MAP_SIZE = 84 * 84

class DQNAgent:
  def __init__(self):
    self.state_size = MAP_SIZE
    self.output_size = MAP_SIZE
    self.learning_rate = 0.5
    self.epsilon = 1
    self.epsilon_min = 0.01
    self.epsilon_decay = 0.995
    self.gamma = 0.9
    self.memory = deque(maxlen=2000)
    self.model = self._build_model()

  def _build_model(self):
    # Neural Net for Deep-Q learning Model
    model = Sequential()
    model.add(Dense(MAP_SIZE, input_dim=self.state_size, activation='relu'))
    model.add(Dense(MAP_SIZE, activation='relu'))
    model.add(Dense(MAP_SIZE, activation='relu'))
    model.add(Dense(MAP_SIZE, activation='relu'))
    model.compile(loss='binary_crossentropy', optimizer='sgd')
    return model

  def act(self, state):
    if numpy.random.rand() <= self.epsilon:
      return numpy.random.randint(0,self.output_size)
    pred_values = self.model.predict(state)
    return numpy.argmax(pred_values)

  def remember(self, state, action, reward, next_state, done):
      self.memory.append((state, action, reward, next_state, done))

  def replay(self, batch_size):
    choice = numpy.random.choice(range(len(self.memory)), batch_size)
    minibatch = [self.memory[index] for index in choice]
    for state, action, reward, next_state, done in minibatch:
      target = reward
      if not done:
        target = (reward + self.gamma *
                  numpy.amax(self.model.predict(next_state)[0]))
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
    self.batch_size = 1000
    self.last_action = None
    self.last_state = None

  def step(self, obs):
    super(DefeatRoaches, self).step(obs)

    if len(self.agent.memory) > self.batch_size:
      self.agent.replay(int(self.batch_size/10))
      self.agent.memory.clear()

    if _ATTACK_SCREEN in obs.observation["available_actions"]:
      player_relative = obs.observation["screen"][_PLAYER_RELATIVE]
      # roach_y, roach_x = (player_relative == _PLAYER_HOSTILE).nonzero()
      # if not roach_y.any():
      #   return actions.FunctionCall(_NO_OP, [])
      # marine_y, marine_x = (player_relative == _PLAYER_FRIENDLY).nonzero()
      # if not marine_y.any():
      #   return actions.FunctionCall(_NO_OP, [])
      # while len(roach_y) < 4:
      #   numpy.append(roach_y, numpy.mean(roach_y))
      #   numpy.append(roach_x, numpy.mean(roach_x))
      # while len(marine_y) < 9:
      #   numpy.append(marine_y, numpy.mean(marine_y))
      #   numpy.append(marine_x, numpy.mean(marine_x))

      state = player_relative.reshape([1,-1])

      if self.last_action is not None:
        reward = obs.reward
        self.agent.remember(self.last_state, self.last_action, reward, state, False)

      self.last_action = self.agent.act(state)
      self.last_state = state

      target = [self.last_action % 84, int(self.last_action / 84)]
      # print("Attack: ", target[0], target[1])
      return actions.FunctionCall(_ATTACK_SCREEN, [_NOT_QUEUED, target])
    elif _SELECT_ARMY in obs.observation["available_actions"]:
      return actions.FunctionCall(_SELECT_ARMY, [_SELECT_ALL])
    else:
      return actions.FunctionCall(_NO_OP, [])
