"""
训练主循环: 编排 Collector 采集 → Learner 训练 → 权重同步 的完整流程。
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

import torch

from .models import ActorCritic
from .ppo import PPO
from .buffer import RolloutBuffer
from .model_factory import ModelFactory
from .distributed import DistributedTrainingContext
from .logger import TensorboardLogger

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    state_dim: int = 10
    action_dim: int = 20
    hidden_dim: int = 256

    lr: float = 3e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    eps_clip: float = 0.2
    k_epochs: int = 10
    batch_size: int = 1024
    value_coef: float = 0.5
    entropy_coef: float = 0.01
    max_grad_norm: float = 0.5

    total_episodes: int = 500
    checkpoint_interval: int = 50
    log_dir: str = "runs/rl_training"
    checkpoint_dir: str = "checkpoints"

    seed: int = 42


class Trainer:
    """
    RL 训练器: 管理完整的训练生命周期。

    职责:
    1. 初始化模型、优化器、DDP 上下文
    2. 每个 episode: collect → compute GAE → PPO update → sync weights
    3. 定期保存 checkpoint
    4. 记录训练指标
    """

    def __init__(
        self,
        config: TrainingConfig,
        collect_fn=None,
        weight_push_fn=None,
    ):
        self.cfg = config
        self.collect_fn = collect_fn
        self.weight_push_fn = weight_push_fn

        self.ctx = DistributedTrainingContext()
        self.model: Optional[ActorCritic] = None
        self.ppo: Optional[PPO] = None
        self.buffer = RolloutBuffer()
        self.tb_logger: Optional[TensorboardLogger] = None
        self.weight_version = 0

    def setup(self):
        """初始化训练环境"""
        torch.manual_seed(self.cfg.seed)

        self.ctx.setup()
        device = self.ctx.device

        self.model = ActorCritic(
            self.cfg.state_dim,
            self.cfg.action_dim,
            self.cfg.hidden_dim,
        )
        self.model = self.ctx.wrap_model(self.model)
        self.buffer = RolloutBuffer(device=device)

        self.ppo = PPO(
            model=self.model,
            lr=self.cfg.lr,
            gamma=self.cfg.gamma,
            gae_lambda=self.cfg.gae_lambda,
            eps_clip=self.cfg.eps_clip,
            k_epochs=self.cfg.k_epochs,
            batch_size=self.cfg.batch_size,
            value_coef=self.cfg.value_coef,
            entropy_coef=self.cfg.entropy_coef,
            max_grad_norm=self.cfg.max_grad_norm,
            device=device,
        )

        if self.ctx.is_main:
            self.tb_logger = TensorboardLogger(self.cfg.log_dir)

        logger.info(f"Trainer initialized on {device}")

    def train(self):
        """执行完整的训练循环"""
        self.setup()

        for ep in range(1, self.cfg.total_episodes + 1):
            ep_start = time.time()

            # 1. Collect
            if self.collect_fn:
                self.collect_fn(self.buffer, self.weight_version)
            else:
                logger.warning("No collect_fn provided, skipping collection")
                continue

            if self.buffer.size() == 0:
                logger.warning(f"Episode {ep}: empty buffer, skipping")
                continue

            # 2. Train
            metrics = self.ppo.update(self.buffer)
            self.buffer.clear()

            # 3. Sync weights
            self.weight_version += 1
            if self.weight_push_fn:
                weights_bytes = ModelFactory.serialize_weights(
                    self.model, is_ddp=self.ctx.is_distributed
                )
                self.weight_push_fn(weights_bytes, self.weight_version)

            # 4. Log
            elapsed = time.time() - ep_start
            metrics["episode"] = ep
            metrics["weight_version"] = self.weight_version
            metrics["episode_time_seconds"] = elapsed

            if self.ctx.is_main:
                self._log_metrics(ep, metrics)

            # 5. Checkpoint
            if ep % self.cfg.checkpoint_interval == 0 and self.ctx.is_main:
                path = f"{self.cfg.checkpoint_dir}/checkpoint_ep{ep}.pt"
                ModelFactory.save_checkpoint(
                    path=path,
                    model=self.model,
                    optimizer=self.ppo.optimizer,
                    epoch=ep,
                    weight_version=self.weight_version,
                    is_ddp=self.ctx.is_distributed,
                )

            self.ctx.barrier()

        self.cleanup()

    def _log_metrics(self, ep: int, metrics: Dict[str, Any]):
        log_str = (
            f"Episode {ep}/{self.cfg.total_episodes} | "
            f"policy_loss={metrics.get('policy_loss', 0):.4f} | "
            f"value_loss={metrics.get('value_loss', 0):.4f} | "
            f"entropy={metrics.get('entropy', 0):.4f} | "
            f"time={metrics.get('episode_time_seconds', 0):.1f}s"
        )
        logger.info(log_str)

        if self.tb_logger:
            self.tb_logger.log(
                {k: v for k, v in metrics.items() if isinstance(v, (int, float))},
                step=ep,
            )

    def cleanup(self):
        if self.tb_logger:
            self.tb_logger.close()
        self.ctx.cleanup()
