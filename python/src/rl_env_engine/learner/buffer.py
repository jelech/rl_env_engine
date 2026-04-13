"""
RolloutBuffer: PPO 数据管道的核心组件。

负责存储 trajectory 数据、计算 GAE advantage、提供 mini-batch 迭代。
"""

import torch
import numpy as np
from typing import Generator, NamedTuple


class RolloutSample(NamedTuple):
    states: torch.Tensor
    actions: torch.Tensor
    returns: torch.Tensor
    advantages: torch.Tensor
    old_log_probs: torch.Tensor


class RolloutBuffer:
    """
    PPO 的 on-policy 数据缓冲区。

    存储 collector 采集的 (state, action, reward, done, log_prob, value)，
    采集完成后计算 GAE advantage 和 discounted return，
    然后通过 mini-batch 迭代器提供给 PPO 训练。
    """

    def __init__(self, device: torch.device = None):
        self.device = device or torch.device("cpu")
        self.states = []
        self.actions = []
        self.rewards = []
        self.dones = []
        self.log_probs = []
        self.values = []

    def add(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        done: bool,
        log_prob: float,
        value: float,
    ):
        self.states.append(state)
        self.actions.append(action)
        self.rewards.append(reward)
        self.dones.append(done)
        self.log_probs.append(log_prob)
        self.values.append(value)

    def add_batch(
        self,
        states: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
        dones: np.ndarray,
        log_probs: np.ndarray,
        values: np.ndarray,
    ):
        """批量添加 transitions (从 S3 加载的 collector 数据)"""
        for i in range(len(states)):
            self.states.append(states[i])
            self.actions.append(int(actions[i]))
            self.rewards.append(float(rewards[i]))
            self.dones.append(bool(dones[i]))
            self.log_probs.append(float(log_probs[i]))
            self.values.append(float(values[i]))

    def size(self) -> int:
        return len(self.states)

    def compute_returns_and_advantages(
        self,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        last_value: float = 0.0,
    ) -> tuple:
        """
        计算 GAE advantage 和 discounted return。

        关键: 在 done=True 处截断折扣累积，不跨 episode 边界。
        """
        n = len(self.rewards)
        advantages = np.zeros(n, dtype=np.float32)
        last_gae = 0.0

        for t in reversed(range(n)):
            if t == n - 1:
                next_value = last_value
                next_non_terminal = 1.0 - float(self.dones[t])
            else:
                next_value = self.values[t + 1]
                next_non_terminal = 1.0 - float(self.dones[t])

            delta = self.rewards[t] + gamma * next_value * next_non_terminal - self.values[t]
            last_gae = delta + gamma * gae_lambda * next_non_terminal * last_gae
            advantages[t] = last_gae

        returns = advantages + np.array(self.values, dtype=np.float32)
        return returns, advantages

    def get_tensors(
        self,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        last_value: float = 0.0,
    ) -> RolloutSample:
        """将 buffer 数据转换为 tensor 并计算 returns/advantages"""
        returns, advantages = self.compute_returns_and_advantages(gamma, gae_lambda, last_value)

        states = torch.tensor(np.array(self.states), dtype=torch.float32, device=self.device)
        actions = torch.tensor(self.actions, dtype=torch.long, device=self.device)
        returns_t = torch.tensor(returns, dtype=torch.float32, device=self.device)
        advantages_t = torch.tensor(advantages, dtype=torch.float32, device=self.device)
        old_log_probs = torch.tensor(self.log_probs, dtype=torch.float32, device=self.device)

        return RolloutSample(states, actions, returns_t, advantages_t, old_log_probs)

    def iterate_minibatches(
        self,
        sample: RolloutSample,
        batch_size: int = 1024,
    ) -> Generator[RolloutSample, None, None]:
        """Mini-batch 迭代器"""
        n = sample.states.shape[0]
        indices = torch.randperm(n, device=self.device)

        for start in range(0, n, batch_size):
            end = min(start + batch_size, n)
            batch_idx = indices[start:end]
            yield RolloutSample(
                states=sample.states[batch_idx],
                actions=sample.actions[batch_idx],
                returns=sample.returns[batch_idx],
                advantages=sample.advantages[batch_idx],
                old_log_probs=sample.old_log_probs[batch_idx],
            )

    def clear(self):
        """
        清空 buffer。显式删除引用以避免内存泄漏。
        """
        del self.states[:]
        del self.actions[:]
        del self.rewards[:]
        del self.dones[:]
        del self.log_probs[:]
        del self.values[:]

        if self.device.type == "cuda":
            torch.cuda.empty_cache()
