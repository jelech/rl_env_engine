"""
Actor-Critic 网络定义。

独立的 Policy 和 Value 网络，不共享 backbone 参数。
博客原文: "共享backbone在训练后期会出现actor和critic的学习目标冲突"
"""

import torch
import torch.nn as nn
from typing import Tuple


class PolicyNetwork(nn.Module):
    """策略网络 (Actor): 输入 state，输出动作概率分布"""

    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256):
        super().__init__()
        self.fc1 = nn.Linear(state_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.action_head = nn.Linear(hidden_dim, action_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return torch.softmax(self.action_head(x), dim=-1)


class ValueNetwork(nn.Module):
    """价值网络 (Critic): 输入 state，输出状态价值 V(s)"""

    def __init__(self, state_dim: int, hidden_dim: int = 256):
        super().__init__()
        self.fc1 = nn.Linear(state_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.value_head = nn.Linear(hidden_dim, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.value_head(x)


class ActorCritic(nn.Module):
    """
    组合的 Actor-Critic 容器，内部持有独立的 policy 和 value 网络。
    提供统一的推理接口。
    """

    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256):
        super().__init__()
        self.policy = PolicyNetwork(state_dim, action_dim, hidden_dim)
        self.value = ValueNetwork(state_dim, hidden_dim)

    def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        action_probs = self.policy(state)
        state_value = self.value(state)
        return action_probs, state_value

    def act(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        采样动作并返回 (action, log_prob, value)。
        用于 collector 端的在线推理。
        """
        action_probs = self.policy(state)
        dist = torch.distributions.Categorical(action_probs)
        action = dist.sample()
        log_prob = dist.log_prob(action)
        value = self.value(state).squeeze(-1)
        return action, log_prob, value

    def evaluate(self, state: torch.Tensor, action: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        评估给定 (state, action) 对的 log_prob, value, entropy。
        用于 PPO 训练时的策略评估。
        """
        action_probs = self.policy(state)
        dist = torch.distributions.Categorical(action_probs)
        log_prob = dist.log_prob(action)
        entropy = dist.entropy()
        value = self.value(state).squeeze(-1)
        return log_prob, value, entropy
