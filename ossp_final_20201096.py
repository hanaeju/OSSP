# -*- coding: utf-8 -*-
"""ossp_final_20201096.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/gist/hanaeju/a6b8eca1c3dc9089937cf0e887274e27/ossp_final_20201096.ipynb
"""

WORLD = 1
STAGE = 1 
LEVEL = f"{WORLD}-{STAGE}"
QUALITY = 0 
DEFAULT_GAME = f"SuperMarioBros-{LEVEL}-v{QUALITY}"
MY_ACTIONS = [["right"], ["right", "A"]]
batches = 10
each_batch_steps = 500000

!pip install -q stable-baselines3[extra] > /dev/null 2>&1
!pip install -q gym-super-mario-bros > /dev/null 2>&1
!pip install -q gym pyvirtualdisplay > /dev/null 2>&1
!apt-get install -q -y xvfb python-opengl ffmpeg > /dev/null 2>&1
!pip install git+https://github.com/tensorflow/docs > /dev/null 2>&1

import os
os.system("Xvfb :1 -screen 0 256x140x24 &")
os.environ['DISPLAY'] = ':1'
from IPython import display as ipythondisplay
from PIL import Image
from pyvirtualdisplay import Display
import base64
import matplotlib.pyplot as plt
import tensorflow_docs.vis.embed as embed
import numpy as np
import torch
import gym
from gym.spaces import Box
import gym_super_mario_bros
from gym.wrappers import FrameStack
from nes_py.wrappers import JoypadSpace
from gym.wrappers import FrameStack
from torchvision import transforms
from stable_baselines3 import PPO

class SkipFrame(gym.Wrapper):
    def __init__(self, env, skip):
        super().__init__(env)
        self._skip = skip

    def step(self, action):
        total_reward = 0.0
        done = False
        for i in range(self._skip):
            obs, reward, done, info = self.env.step(action)
            total_reward += reward
            if done:
                break
        return obs, total_reward, done, info


class GrayScaleObservation(gym.ObservationWrapper):
    def __init__(self, env):
        super().__init__(env)
        obs_shape = self.observation_space.shape[:2]
        self.observation_space = Box(low=0, high=255, shape=obs_shape, dtype=np.uint8)

    def permute_orientation(self, observation):
        observation = np.transpose(observation, (2, 0, 1))
        observation = torch.tensor(observation.copy(), dtype=torch.float)
        return observation

    def observation(self, observation):
        observation = self.permute_orientation(observation)
        transform = transforms.Grayscale()
        observation = transform(observation)
        return observation


class ResizeObservation(gym.ObservationWrapper):
    def __init__(self, env, shape):
        super().__init__(env)
        if isinstance(shape, int):
            self.shape = (shape, shape)
        else:
            self.shape = tuple(shape)

        obs_shape = self.shape + self.observation_space.shape[2:]
        self.observation_space = Box(low=0, high=255, shape=obs_shape, dtype=np.uint8)

    def observation(self, observation):
        my_transforms = transforms.Compose(
            [transforms.Resize(self.shape), transforms.Normalize(0, 255)]
        )
        observation = my_transforms(observation).squeeze(0)
        return observation

def build_env():
  env = gym_super_mario_bros.make(DEFAULT_GAME)
  env = SkipFrame(env, skip=4)
  env = GrayScaleObservation(env)
  env = ResizeObservation(env, shape=84)
  env = FrameStack(env, num_stack=4)
  env = JoypadSpace(env, MY_ACTIONS)
  return env

display = Display(visible=0, size=(400, 300))
display.start()


def save_gif(model, image_file, max_steps=2000):
  best_img = []
  all_rewards = []
  best_reward = 0
  for i in range(20):
    env = build_env()
    screen = env.render(mode='rgb_array')
    im = Image.fromarray(screen)
    images = [im]
    obs = env.reset()
    cur_best_reward = 0
    for i in range(1, max_steps + 1):
      b = torch.Tensor(4, 84, 84)
      torch.stack(obs._frames, out=b)
      action, _ = model.predict(b.numpy())

      obs, reward, done, _ = env.step(action.tolist())
      cur_best_reward += reward

      if i % 2 == 0:
        screen = env.render(mode='rgb_array')
        images.append(Image.fromarray(screen))
      if done:
        break
    all_rewards.append(cur_best_reward)
    if cur_best_reward > best_reward or (
        cur_best_reward == best_reward and len(images) > len(best_img)
    ):
      best_reward = cur_best_reward
      best_img = images
  best_img[0].save(
      image_file, save_all=True, append_images=best_img[1:], loop=0, duration=1)

prefix = "ppo_cnn_"
!mkdir -p "/content/mario_rl/models"
!mkdir -p "/content/mario_rl/videos"

model = PPO('CnnPolicy', build_env(), verbose=0)

base_steps = 0 
total_steps = base_steps
for i in range(1, 1 + batches):
  obs = model.env.reset()
  model.learn(total_timesteps=each_batch_steps)
  total_steps += each_batch_steps
  if each_batch_steps > 50000: 
    model.save(f"/content/mario_rl/models/model_{total_steps}")
  save_gif(model, f"/content/mario_rl/videos/model_{total_steps}.gif")

embed.embed_file(f"/content/mario_rl/videos/model_{total_steps}.gif")

