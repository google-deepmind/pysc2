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
num_episodes = 1

FLAGS = flags.FLAGS

class Agent:
    def __init__(self):
        FLAGS(sys.argv)
        self.env =  sc2_env.SC2Env("CollectMineralShards", step_mul=step_mul, visualize=True)
        
    def play(self):
        total_reward = 0.0
        for episode in range(num_episodes):
    
            obs = self.env.reset()
            # Select all marines first
            obs = self.env.step(actions=[actions.FunctionCall(_SELECT_ARMY, [_SELECT_ALL])])
            
            done = False
            while not done:
                # generate a random coordinate
                coord = [np.random.randint(64), np.random.randint(64)]
                
                # move to that coordinate
                obs = self.env.step(actions =[actions.FunctionCall(_MOVE_SCREEN, [_NOT_QUEUED, coord])])
                
                # example of processing player relative minimap
                player_relative = obs[0].observation["screen"][_PLAYER_RELATIVE]

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