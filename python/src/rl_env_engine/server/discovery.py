"""
服务发现模块 - 基于 Redis 的服务注册与发现
"""

import os
import time
import socket
import threading
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class ServiceDiscovery:
    """
    服务发现类 - 管理服务的注册和发现

    使用 Redis Sorted Set 存储服务地址，score 为过期时间戳
    """

    def __init__(
        self,
        redis_url: str = None,
        scenario_name: str = "rl_env_engine",
        ttl: int = 10,
    ):
        """
        初始化服务发现

        Args:
            redis_url: Redis 连接 URL，默认从环境变量 REDIS_URL 读取
            scenario_name: 场景名称，用于区分不同服务
            ttl: 服务存活时间（秒）
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.scenario_name = scenario_name
        self.ttl = ttl
        self.ips_key = f"{scenario_name}:ips"

        self._redis_client = None
        self._refresh_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._registered_addr: Optional[str] = None

    def _get_redis_client(self):
        """延迟初始化 Redis 客户端"""
        if self._redis_client is None:
            try:
                import redis

                self._redis_client = redis.Redis.from_url(self.redis_url)
                # 清理过期服务
                self._redis_client.zremrangebyscore(self.ips_key, "-inf", int(time.time()) - 60)
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                raise
        return self._redis_client

    def get_advertised_addr(self, port: int) -> str:
        """
        获取对外广播的地址

        优先使用环境变量配置（适用于 Docker），否则自动检测
        """
        adv_ip = os.getenv("ADVERTISED_IP")
        adv_port = os.getenv("ADVERTISED_PORT")

        if not adv_ip:
            try:
                adv_ip = socket.gethostbyname(socket.gethostname())
            except Exception:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    adv_ip = s.getsockname()[0]
                    s.close()
                except Exception:
                    adv_ip = "127.0.0.1"

        if not adv_port:
            adv_port = str(port)

        return f"{adv_ip}:{adv_port}"

    def register(self, port: int) -> str:
        """
        注册服务并启动心跳线程

        Args:
            port: 服务端口

        Returns:
            注册的地址
        """
        self._registered_addr = self.get_advertised_addr(port)

        # 立即注册一次
        self._do_register()

        # 启动心跳线程
        self._stop_event.clear()
        self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._refresh_thread.start()

        logger.info(f"Service registered at {self._registered_addr}")
        return self._registered_addr

    def _do_register(self):
        """执行一次注册"""
        try:
            client = self._get_redis_client()
            client.zadd(self.ips_key, {self._registered_addr: int(time.time()) + self.ttl})
        except Exception as e:
            logger.error(f"Failed to register service: {e}")

    def _refresh_loop(self):
        """心跳刷新循环"""
        while not self._stop_event.is_set():
            try:
                self._do_register()
            except Exception as e:
                logger.error(f"Refresh registration error: {e}")

            # 等待 TTL/2 秒后刷新
            self._stop_event.wait(self.ttl / 2)

    def unregister(self):
        """注销服务"""
        self._stop_event.set()

        if self._registered_addr:
            try:
                client = self._get_redis_client()
                client.zrem(self.ips_key, self._registered_addr)
                logger.info(f"Service unregistered: {self._registered_addr}")
            except Exception as e:
                logger.error(f"Failed to unregister service: {e}")

        if self._refresh_thread and self._refresh_thread.is_alive():
            self._refresh_thread.join(timeout=2)

    def get_services(self) -> List[str]:
        """
        获取所有存活的服务地址

        Returns:
            服务地址列表
        """
        try:
            client = self._get_redis_client()
            current_time = int(time.time()) - self.ttl
            ips = client.zrangebyscore(self.ips_key, current_time, "+inf")
            return [ip.decode("utf-8") if isinstance(ip, bytes) else ip for ip in ips]
        except Exception as e:
            logger.error(f"Failed to get services: {e}")
            return []

    def __del__(self):
        """析构时注销服务"""
        self.unregister()
