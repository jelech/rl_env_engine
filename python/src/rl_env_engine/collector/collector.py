"""
Python 端 Collector: 连接 Go 仿真 worker，执行 CPU 推理，组装 RolloutBuffer。
"""

import logging
import time
from typing import List, Optional

import numpy as np
import torch

from ..learner.models import ActorCritic
from ..learner.buffer import RolloutBuffer
from ..learner.model_factory import ModelFactory
from ..client.grpc_env import GrpcEnv
from .weight_receiver import WeightReceiver

logger = logging.getLogger(__name__)


class PythonCollector:
    """
    Python 端 Collector。

    职责:
    1. 连接多个 Go 仿真 worker (通过 GrpcEnv)
    2. 使用本地持有的 PolicyNetwork 做 CPU 推理
    3. 驱动 step 循环，组装 RolloutBuffer
    4. 订阅 Redis 权重更新
    """

    def __init__(
        self,
        collector_id: str,
        worker_addresses: List[dict],
        model: ActorCritic,
        redis_url: str = "",
        model_key: str = "default",
    ):
        """
        Args:
            collector_id: collector 标识
            worker_addresses: 仿真 worker 地址列表, 每项 {"scenario": ..., "host": ..., "port": ...}
            model: ActorCritic 模型 (CPU 推理)
            redis_url: Redis URL (用于权重订阅)
            model_key: 模型 key
        """
        self.collector_id = collector_id
        self.model = model
        self.model.eval()

        self.envs: List[GrpcEnv] = []
        for addr in worker_addresses:
            env = GrpcEnv(
                scenario=addr["scenario"],
                host=addr.get("host", "127.0.0.1"),
                port=addr.get("port", 9090),
            )
            self.envs.append(env)

        self.weight_receiver: Optional[WeightReceiver] = None
        if redis_url:
            self.weight_receiver = WeightReceiver(
                redis_url=redis_url,
                model_key=model_key,
            )

        self._episodes_completed = 0
        self._total_steps = 0

    def start_weight_subscription(self):
        """启动后台权重订阅"""
        if self.weight_receiver is None:
            return

        def _on_update(weights_bytes: bytes, version: int):
            ModelFactory.load_weights_from_bytes(self.model, weights_bytes)
            self.model.eval()

        self.weight_receiver.start(_on_update)

    def collect(self, buffer: RolloutBuffer, weight_version: int = 0) -> float:
        """
        执行一轮采集: 每个 env 跑一个 episode。

        Returns:
            平均 episode reward
        """
        total_reward = 0.0

        for env in self.envs:
            ep_reward = self._collect_one_episode(env, buffer)
            total_reward += ep_reward
            self._episodes_completed += 1

        avg_reward = total_reward / max(len(self.envs), 1)
        logger.info(
            f"Collector {self.collector_id}: collected {len(self.envs)} episodes, "
            f"avg_reward={avg_reward:.2f}, buffer_size={buffer.size()}"
        )
        return avg_reward

    def _collect_one_episode(self, env: GrpcEnv, buffer: RolloutBuffer) -> float:
        obs, _ = env.reset()
        episode_reward = 0.0

        while True:
            state_tensor = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)

            with torch.no_grad():
                action, log_prob, value = self.model.act(state_tensor)

            action_val = action.item()
            log_prob_val = log_prob.item()
            value_val = value.item()

            next_obs, reward, terminated, truncated, info = env.step(action_val)

            done = terminated or truncated
            buffer.add(obs, action_val, reward, done, log_prob_val, value_val)

            episode_reward += reward
            self._total_steps += 1

            if done:
                break

            obs = next_obs

        return episode_reward

    @property
    def stats(self) -> dict:
        return {
            "collector_id": self.collector_id,
            "episodes_completed": self._episodes_completed,
            "total_steps": self._total_steps,
            "num_envs": len(self.envs),
            "weight_version": (
                self.weight_receiver.current_version if self.weight_receiver else 0
            ),
        }

    def close(self):
        if self.weight_receiver:
            self.weight_receiver.stop()
        for env in self.envs:
            try:
                env.close()
            except Exception as e:
                logger.warning(f"Error closing env: {e}")
