"""
权重接收器: 订阅 Redis 权重更新，自动拉取并加载新权重。
"""

import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class WeightReceiver:
    """
    Redis pub/sub 权重订阅器。

    收到 Learner 推送的版本号通知后，自动拉取权重并调用回调。
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        model_key: str = "default",
        prefix: str = "rl",
    ):
        self.model_key = model_key
        self._prefix = prefix
        self._stop_event = threading.Event()
        self._current_version = 0
        self._thread: Optional[threading.Thread] = None

        try:
            import redis
            self._redis = redis.Redis.from_url(redis_url)
            self._enabled = True
        except ImportError:
            logger.warning("redis not installed, weight receiver disabled")
            self._redis = None
            self._enabled = False

    def _weight_key(self) -> str:
        return f"{self._prefix}:weights:{self.model_key}"

    def _version_key(self) -> str:
        return f"{self._prefix}:version:{self.model_key}"

    def _channel_key(self) -> str:
        return f"{self._prefix}:updates:{self.model_key}"

    @property
    def current_version(self) -> int:
        return self._current_version

    def get_latest_weights(self) -> Optional[bytes]:
        """主动拉取最新权重"""
        if not self._enabled:
            return None
        import json
        raw = self._redis.get(self._weight_key())
        if raw is None:
            return None
        data = json.loads(raw)
        self._current_version = data.get("version", 0)
        import base64
        return base64.b64decode(data["data"]) if isinstance(data["data"], str) else data["data"]

    def start(self, on_update: Callable[[bytes, int], None]):
        """
        启动后台订阅线程。

        Args:
            on_update: 回调函数 (weights_bytes, version)
        """
        if not self._enabled:
            logger.warning("Weight receiver not available")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._subscribe_loop,
            args=(on_update,),
            daemon=True,
        )
        self._thread.start()
        logger.info(f"Weight receiver started for model_key={self.model_key}")

    def _subscribe_loop(self, on_update: Callable[[bytes, int], None]):
        pubsub = self._redis.pubsub()
        pubsub.subscribe(self._channel_key())

        try:
            while not self._stop_event.is_set():
                msg = pubsub.get_message(timeout=1.0)
                if msg is None or msg["type"] != "message":
                    continue

                try:
                    version = int(msg["data"])
                except (ValueError, TypeError):
                    continue

                if version <= self._current_version:
                    continue

                weights = self.get_latest_weights()
                if weights is not None:
                    on_update(weights, self._current_version)
                    logger.info(f"Loaded weight version {self._current_version}")
        except Exception as e:
            logger.error(f"Weight subscription error: {e}")
        finally:
            pubsub.unsubscribe()
            pubsub.close()

    def wait_for_version(self, target_version: int, timeout: float = 300.0) -> bool:
        """阻塞等待指定版本 (sync barrier)"""
        start = time.time()
        while self._current_version < target_version:
            if time.time() - start > timeout:
                return False
            time.sleep(0.1)
        return True

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
