"""
分布式训练上下文: DDP 初始化、rank 管理、advantage 全局归一化。
"""

import os
import logging
from typing import Optional

import torch
import torch.distributed as dist
import torch.nn as nn
from torch.nn.parallel import DistributedDataParallel as DDP

logger = logging.getLogger(__name__)


class DistributedTrainingContext:
    """
    DDP 训练上下文管理器。

    使用:
        ctx = DistributedTrainingContext()
        ctx.setup()
        model = ctx.wrap_model(model)
        ...
        ctx.cleanup()
    """

    def __init__(self, backend: Optional[str] = None):
        self._backend = backend
        self._rank = 0
        self._world_size = 1
        self._device = torch.device("cpu")
        self._is_distributed = False

    @property
    def rank(self) -> int:
        return self._rank

    @property
    def world_size(self) -> int:
        return self._world_size

    @property
    def device(self) -> torch.device:
        return self._device

    @property
    def is_main(self) -> bool:
        return self._rank == 0

    @property
    def is_distributed(self) -> bool:
        return self._is_distributed

    def setup(self):
        """初始化分布式训练环境 (由 torchrun 启动时自动设置环境变量)"""
        if "RANK" not in os.environ:
            logger.info("Non-distributed mode (no RANK env var)")
            if torch.cuda.is_available():
                self._device = torch.device("cuda:0")
            return

        backend = self._backend
        if backend is None:
            backend = "nccl" if torch.cuda.is_available() else "gloo"

        dist.init_process_group(backend)
        self._rank = dist.get_rank()
        self._world_size = dist.get_world_size()
        self._is_distributed = True

        if torch.cuda.is_available():
            self._device = torch.device(f"cuda:{self._rank}")
            torch.cuda.set_device(self._device)

        logger.info(f"DDP initialized: rank={self._rank}, world_size={self._world_size}, device={self._device}")

    def wrap_model(self, model: nn.Module) -> nn.Module:
        """将模型包装为 DDP"""
        model = model.to(self._device)
        if not self._is_distributed:
            return model
        return DDP(model, device_ids=[self._rank] if torch.cuda.is_available() else None)

    def normalize_advantages_global(self, advantages: torch.Tensor) -> torch.Tensor:
        """
        全局 advantage 归一化: 使用 all_reduce 计算全局均值和方差。

        在 DDP 场景下，每张 GPU 只持有部分数据，
        直接做局部归一化会导致收敛变慢。
        """
        if not self._is_distributed:
            return (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        n = torch.tensor([advantages.numel()], dtype=torch.float64, device=self._device)
        s = advantages.sum().double()
        ss = (advantages ** 2).sum().double()

        dist.all_reduce(n, op=dist.ReduceOp.SUM)
        dist.all_reduce(s, op=dist.ReduceOp.SUM)
        dist.all_reduce(ss, op=dist.ReduceOp.SUM)

        mean = (s / n).float()
        var = ((ss / n) - (s / n) ** 2).float().clamp(min=1e-8)
        std = var.sqrt()

        return (advantages - mean) / (std + 1e-8)

    def barrier(self):
        """同步屏障"""
        if self._is_distributed:
            dist.barrier()

    def cleanup(self):
        """清理分布式环境"""
        if self._is_distributed:
            dist.destroy_process_group()
            self._is_distributed = False
            logger.info("DDP process group destroyed")

    def __enter__(self):
        self.setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
