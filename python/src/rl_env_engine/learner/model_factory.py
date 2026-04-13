"""
模型工厂: checkpoint 保存/加载、DDP 解包装、ONNX 导出。
"""

import io
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class ModelFactory:
    """管理模型的序列化、反序列化和格式转换"""

    @staticmethod
    def get_model_for_saving(model: nn.Module, is_ddp: bool) -> nn.Module:
        """DDP 模型解包装"""
        return model.module if is_ddp else model

    @staticmethod
    def save_checkpoint(
        path: str,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        epoch: int,
        weight_version: int,
        is_ddp: bool = False,
        extra: Optional[Dict[str, Any]] = None,
    ):
        raw_model = ModelFactory.get_model_for_saving(model, is_ddp)
        checkpoint = {
            "model_state_dict": raw_model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "epoch": epoch,
            "weight_version": weight_version,
        }
        if extra:
            checkpoint.update(extra)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        torch.save(checkpoint, path)
        logger.info(f"Checkpoint saved to {path} (version={weight_version})")

    @staticmethod
    def load_checkpoint(
        path: str,
        model: nn.Module,
        optimizer: Optional[torch.optim.Optimizer] = None,
        device: Optional[torch.device] = None,
    ) -> Dict[str, Any]:
        map_location = device or "cpu"
        checkpoint = torch.load(path, map_location=map_location, weights_only=False)
        model.load_state_dict(checkpoint["model_state_dict"])
        if optimizer and "optimizer_state_dict" in checkpoint:
            optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        logger.info(f"Checkpoint loaded from {path}")
        return checkpoint

    @staticmethod
    def serialize_weights(model: nn.Module, is_ddp: bool = False) -> bytes:
        """将模型权重序列化为 bytes (用于 Redis/gRPC 传输)"""
        raw_model = ModelFactory.get_model_for_saving(model, is_ddp)
        buffer = io.BytesIO()
        torch.save(raw_model.state_dict(), buffer)
        return buffer.getvalue()

    @staticmethod
    def load_weights_from_bytes(model: nn.Module, data: bytes, device: Optional[torch.device] = None):
        """从 bytes 反序列化加载权重"""
        buffer = io.BytesIO(data)
        map_location = device or "cpu"
        state_dict = torch.load(buffer, map_location=map_location, weights_only=True)
        model.load_state_dict(state_dict)

    @staticmethod
    def export_onnx(
        model: nn.Module,
        path: str,
        state_dim: int,
        is_ddp: bool = False,
        batch_size: int = 1,
    ):
        """导出 ONNX 格式用于线上 CPU 推理"""
        raw_model = ModelFactory.get_model_for_saving(model, is_ddp)
        raw_model.eval()

        dummy_input = torch.randn(batch_size, state_dim)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        torch.onnx.export(
            raw_model,
            dummy_input,
            path,
            input_names=["state"],
            output_names=["output"],
            dynamic_axes={"state": {0: "batch"}, "output": {0: "batch"}},
            opset_version=17,
        )
        logger.info(f"ONNX model exported to {path}")
