import sys
import gflags as flags
import random
import numpy as np 

from pysc2.lib import actions as actions
from pysc2.env import sc2_env
from pysc2.env import environment
from pysc2.lib import features

# Define your Starcaft parameters
step_mul = 4

# Starcraft Constants
_MOVE_SCREEN = actions.FUNCTIONS.Move_screen.id
_SELECT_ARMY = actions.FUNCTIONS.select_army.id
_PLAYER_RELATIVE = features.SCREEN_FEATURES.player_relative.index
_NOT_QUEUED = [0]
_SELECT_ALL = [0]

# Define your Agent parameters
num_episodes = 5

FLAGS = flags.FLAGS

def sigmoid(x):
        return 1 / (1 + np.exp(-x))

class Model(object):

    # Initialize network weights
    def __init__(self):
        # 4096 input pixels, 20 hidden units, output 2 numbers (two coordinates)
        self.weights = [np.random.randn(4096, 20), np.random.randn(20, 2), np.random.randn(1, 20)]
        
    # Run network (maybe convolution on minimap input)
    def predict(self, inp):
        # A simple example 2 layer network
        out = inp.flatten()
        out = sigmoid(np.dot(out, self.weights[0]) + self.weights[2])
        out = sigmoid(np.dot(out, self.weights[1]))
        out = 64*np.absolute(out[0]) # return two coordinates from 0 to 64
        return out
    
class Agent:

    def __init__(self):
        FLAGS(sys.argv)
        self.model = Model()
        self.env =  sc2_env.SC2Env("CollectMineralShards", step_mul=step_mul, visualize=True)

    def play(self):
        total_reward = 0.0
        for episode in range(num_episodes):
            obs = self.env.reset()
            # Select all marines first
            obs = self.env.step(actions=[actions.FunctionCall(_SELECT_ARMY, [_SELECT_ALL])])
            
            done = False
            while not done:
                # process player relative minimap
                player_relative = obs[0].observation["screen"][_PLAYER_RELATIVE]

                # Run network on the observation
                coord = self.model.predict(player_relative)

                # move to that coordinate
                obs = self.env.step(actions =[actions.FunctionCall(_MOVE_SCREEN, [_NOT_QUEUED, coord])])
                
                # get reward
                reward = obs[0].reward
                total_reward += reward

                done = obs[0].step_type == environment.StepType.LAST
                if done:
                     obs = self.env.reset()
                     self.env.step(actions=[actions.FunctionCall(_SELECT_ARMY, [_SELECT_ALL])])

        self.env.close()
        return total_reward/num_episodes

if __name__ == "__main__":
    agent = Agent()
    averageReward = agent.play()
    print('Average Reward', averageReward)