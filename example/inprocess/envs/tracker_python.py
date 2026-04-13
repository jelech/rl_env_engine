"""
Pure Python 环境示例 - 1D Tracker

状态: [position, target]
动作: velocity ∈ [-1, 1]
奖励: -|position - target|
结束: step_count >= max_steps
"""

import numpy as np


class TrackerEnv:
    def __init__(self, config=None):
        config = config or {}
        self.target = config.get("target", 1.0)
        self.max_steps = config.get("max_steps", 200)
        self.dt = config.get("dt", 0.1)
        self.noise_scale = config.get("noise", 0.01)
        self.position = 0.0
        self.step_count = 0

    def reset(self, **kwargs):
        self.position = 0.0
        self.step_count = 0
        return np.array([self.position, self.target], dtype=np.float64), {}

    def step(self, action):
        if isinstance(action, np.ndarray):
            action = float(action.flat[0])
        action = max(-1.0, min(1.0, float(action)))

        self.position += action * self.dt + np.random.randn() * self.noise_scale
        self.step_count += 1

        reward = -abs(self.position - self.target)
        done = self.step_count >= self.max_steps
        obs = np.array([self.position, self.target], dtype=np.float64)
        return obs, reward, done, False, {}

    def close(self):
        pass
