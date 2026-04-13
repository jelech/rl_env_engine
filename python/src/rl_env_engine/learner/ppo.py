"""
PPO (Proximal Policy Optimization) 算法实现。

L = L_clip + c1 * L_value - c2 * H[π]
"""

import torch
import torch.nn as nn
from typing import Dict

from .models import ActorCritic
from .buffer import RolloutBuffer, RolloutSample


class PPO:
    """
    PPO 训练器。

    参数:
        model: ActorCritic 模型
        lr: 学习率 (default 3e-4)
        gamma: 折扣因子 (default 0.99)
        gae_lambda: GAE lambda (default 0.95)
        eps_clip: PPO 裁剪系数 (default 0.2)
        k_epochs: 每次更新的 epoch 数 (default 10)
        batch_size: mini-batch 大小 (default 1024)
        value_coef: value loss 系数 (default 0.5)
        entropy_coef: entropy bonus 系数 (default 0.01)
        max_grad_norm: 梯度裁剪阈值 (default 0.5)
    """

    def __init__(
        self,
        model: ActorCritic,
        lr: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        eps_clip: float = 0.2,
        k_epochs: int = 10,
        batch_size: int = 1024,
        value_coef: float = 0.5,
        entropy_coef: float = 0.01,
        max_grad_norm: float = 0.5,
        device: torch.device = None,
    ):
        self.model = model
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.eps_clip = eps_clip
        self.k_epochs = k_epochs
        self.batch_size = batch_size
        self.value_coef = value_coef
        self.entropy_coef = entropy_coef
        self.max_grad_norm = max_grad_norm
        self.device = device or torch.device("cpu")

        self.optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        self.mse_loss = nn.MSELoss()

    def update(self, buffer: RolloutBuffer) -> Dict[str, float]:
        """
        执行一次 PPO 更新 (K epochs of minibatch SGD)。

        Returns:
            包含 policy_loss, value_loss, entropy, total_loss 的 metrics 字典
        """
        sample = buffer.get_tensors(
            gamma=self.gamma,
            gae_lambda=self.gae_lambda,
        )

        # advantage 归一化
        adv = sample.advantages
        adv = (adv - adv.mean()) / (adv.std() + 1e-8)
        sample = RolloutSample(
            states=sample.states,
            actions=sample.actions,
            returns=sample.returns,
            advantages=adv,
            old_log_probs=sample.old_log_probs,
        )

        total_policy_loss = 0.0
        total_value_loss = 0.0
        total_entropy = 0.0
        num_updates = 0

        for _ in range(self.k_epochs):
            for batch in buffer.iterate_minibatches(sample, self.batch_size):
                metrics = self._update_step(batch)
                total_policy_loss += metrics["policy_loss"]
                total_value_loss += metrics["value_loss"]
                total_entropy += metrics["entropy"]
                num_updates += 1

        return {
            "policy_loss": total_policy_loss / num_updates,
            "value_loss": total_value_loss / num_updates,
            "entropy": total_entropy / num_updates,
            "total_loss": (total_policy_loss + total_value_loss) / num_updates,
            "num_updates": num_updates,
        }

    def _update_step(self, batch: RolloutSample) -> Dict[str, float]:
        """单个 mini-batch 的梯度更新步骤"""

        new_log_probs, values, entropy = self.model.evaluate(batch.states, batch.actions)

        # importance sampling ratio
        ratio = torch.exp(new_log_probs - batch.old_log_probs)

        # clipped surrogate loss
        surr1 = ratio * batch.advantages
        surr2 = torch.clamp(ratio, 1.0 - self.eps_clip, 1.0 + self.eps_clip) * batch.advantages
        policy_loss = -torch.min(surr1, surr2).mean()

        # value loss
        value_loss = self.mse_loss(values, batch.returns)

        # entropy bonus
        entropy_loss = -entropy.mean()

        loss = policy_loss + self.value_coef * value_loss + self.entropy_coef * entropy_loss

        self.optimizer.zero_grad(set_to_none=True)
        loss.backward()
        # 梯度裁剪必须在 AllReduce 之后、step 之前
        nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
        self.optimizer.step()

        return {
            "policy_loss": policy_loss.item(),
            "value_loss": value_loss.item(),
            "entropy": -entropy_loss.item(),
        }
