"""
端到端训练示例: CartPole + PPO

使用方式:
1. 单机单卡:
   python example/training/run_cartpole_training.py

2. 先启动 Go 仿真服务 (可选，默认使用本地环境):
   cd go && go run cmd/server/main.go

3. DDP 多卡:
   torchrun --nproc_per_node=4 example/training/run_cartpole_training.py
"""

import logging
import subprocess
import sys
import time
import signal
import os

import numpy as np
import torch

from rl_env_engine.learner.models import ActorCritic
from rl_env_engine.learner.ppo import PPO
from rl_env_engine.learner.buffer import RolloutBuffer
from rl_env_engine.learner.model_factory import ModelFactory
from rl_env_engine.learner.distributed import DistributedTrainingContext

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class CartPoleLocalEnv:
    """
    极简版 CartPole 本地环境 (不依赖 Go server)。
    适合快速验证训练流程。
    """

    def __init__(self):
        try:
            import gymnasium as gym
            self.env = gym.make("CartPole-v1")
            self._use_gym = True
        except ImportError:
            self._use_gym = False
            self._state = None

    def reset(self):
        if self._use_gym:
            obs, info = self.env.reset()
            return obs.astype(np.float32), info
        self._state = np.random.uniform(-0.05, 0.05, size=4).astype(np.float32)
        return self._state, {}

    def step(self, action):
        if self._use_gym:
            obs, reward, terminated, truncated, info = self.env.step(int(action))
            return obs.astype(np.float32), float(reward), terminated, truncated, info

        # 简化物理模拟 (仅用于无 gymnasium 的环境)
        self._state += np.random.randn(4).astype(np.float32) * 0.1
        done = abs(self._state[2]) > 0.42
        reward = 0.0 if done else 1.0
        return self._state.copy(), reward, done, False, {}

    def close(self):
        if self._use_gym:
            self.env.close()


def collect_episode(env, model, buffer):
    """采集一个 episode 的数据"""
    obs, _ = env.reset()
    episode_reward = 0.0

    for _ in range(500):
        state_t = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            action, log_prob, value = model.act(state_t)

        next_obs, reward, terminated, truncated, _ = env.step(action.item())
        done = terminated or truncated
        buffer.add(obs, action.item(), reward, done, log_prob.item(), value.item())
        episode_reward += reward

        if done:
            break
        obs = next_obs

    return episode_reward


def main():
    ctx = DistributedTrainingContext()
    ctx.setup()

    state_dim = 4
    action_dim = 2
    hidden_dim = 64

    model = ActorCritic(state_dim, action_dim, hidden_dim)
    model = ctx.wrap_model(model)

    ppo = PPO(
        model=model,
        lr=3e-4,
        gamma=0.99,
        gae_lambda=0.95,
        eps_clip=0.2,
        k_epochs=10,
        batch_size=64,
        max_grad_norm=0.5,
        device=ctx.device,
    )

    num_envs = 4
    envs = [CartPoleLocalEnv() for _ in range(num_envs)]

    total_episodes = 200
    log_interval = 10
    reward_history = []

    logger.info(f"Training CartPole: {total_episodes} episodes, {num_envs} parallel envs")

    for ep in range(1, total_episodes + 1):
        buffer = RolloutBuffer(device=ctx.device)

        ep_rewards = []
        for env in envs:
            r = collect_episode(env, model, buffer)
            ep_rewards.append(r)

        metrics = ppo.update(buffer)
        avg_reward = np.mean(ep_rewards)
        reward_history.append(avg_reward)
        buffer.clear()

        if ep % log_interval == 0 and ctx.is_main:
            recent = np.mean(reward_history[-log_interval:])
            logger.info(
                f"Episode {ep}/{total_episodes} | "
                f"avg_reward={avg_reward:.1f} | "
                f"recent_{log_interval}_avg={recent:.1f} | "
                f"policy_loss={metrics['policy_loss']:.4f} | "
                f"entropy={metrics['entropy']:.4f}"
            )

    if ctx.is_main:
        ModelFactory.save_checkpoint(
            path="checkpoints/cartpole_final.pt",
            model=model,
            optimizer=ppo.optimizer,
            epoch=total_episodes,
            weight_version=total_episodes,
            is_ddp=ctx.is_distributed,
        )

        ModelFactory.export_onnx(
            model=model.module if ctx.is_distributed else model.policy,
            path="checkpoints/cartpole_policy.onnx",
            state_dim=state_dim,
            is_ddp=False,
        )

        final_avg = np.mean(reward_history[-20:])
        logger.info(f"Training complete. Final 20-episode avg reward: {final_avg:.1f}")

    for env in envs:
        env.close()
    ctx.cleanup()


if __name__ == "__main__":
    main()
