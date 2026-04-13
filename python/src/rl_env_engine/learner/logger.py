"""
训练日志与监控: TensorBoard 日志 + Prometheus metrics helper。
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class TensorboardLogger:
    """TensorBoard 日志记录器"""

    def __init__(self, log_dir: str):
        try:
            from torch.utils.tensorboard import SummaryWriter
            self.writer = SummaryWriter(log_dir)
            self._enabled = True
        except ImportError:
            logger.warning("tensorboard not installed, logging disabled")
            self.writer = None
            self._enabled = False

    def log(self, metrics: Dict[str, float], step: int):
        if not self._enabled:
            return
        for k, v in metrics.items():
            self.writer.add_scalar(k, v, step)

    def log_histogram(self, tag: str, values, step: int):
        if not self._enabled:
            return
        self.writer.add_histogram(tag, values, step)

    def flush(self):
        if self._enabled:
            self.writer.flush()

    def close(self):
        if self._enabled:
            self.writer.close()


class PrometheusMetrics:
    """Prometheus metrics 导出 helper (可选依赖)"""

    def __init__(self, prefix: str = "rl_learner"):
        self._prefix = prefix
        self._metrics = {}
        try:
            from prometheus_client import Gauge, Counter, Histogram
            self._gauge_cls = Gauge
            self._counter_cls = Counter
            self._histogram_cls = Histogram
            self._enabled = True
        except ImportError:
            self._enabled = False
            logger.info("prometheus_client not installed, metrics disabled")

    def gauge(self, name: str, description: str = ""):
        if not self._enabled:
            return _NoOpMetric()
        full_name = f"{self._prefix}_{name}"
        if full_name not in self._metrics:
            self._metrics[full_name] = self._gauge_cls(full_name, description or name)
        return self._metrics[full_name]

    def counter(self, name: str, description: str = ""):
        if not self._enabled:
            return _NoOpMetric()
        full_name = f"{self._prefix}_{name}"
        if full_name not in self._metrics:
            self._metrics[full_name] = self._counter_cls(full_name, description or name)
        return self._metrics[full_name]


class _NoOpMetric:
    """不启用 prometheus 时的空操作占位"""
    def set(self, *a, **kw): pass
    def inc(self, *a, **kw): pass
    def observe(self, *a, **kw): pass
