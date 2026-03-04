"""
RL Env Engine SDK - 高级客户端 SDK

支持：
- 服务发现（从 Redis 获取可用 Worker）
- 队列调度（当 Worker 不够时排队处理）
- 批量执行（并发调用多个 Worker）
- 重试机制

基于 RL4SCS/envs/sdk.py 的模式设计
"""

import io
import os
import uuid
import time
import queue
import base64
import logging
import requests
import concurrent.futures
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


def retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """通用重试装饰器"""

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for i in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if i == max_retries:
                        raise e
                    logger.warning(f"Retry {i+1}/{max_retries} for {func.__name__} after error: {e}")
                    time.sleep(delay)
                    delay *= backoff

        return wrapper

    return decorator


class SimulationSDK:
    """
    仿真 SDK - 高级客户端

    提供服务发现、会话管理、批量执行等功能
    """

    def __init__(
        self,
        discovery_url: str = None,
        direct_workers: List[str] = None,
        timeout: int = 30,
    ):
        """
        初始化 SDK

        Args:
            discovery_url: 服务发现 URL（如 http://localhost:8000/ips）
            direct_workers: 直接指定 Worker 地址列表（不使用服务发现）
            timeout: 请求超时时间（秒）
        """
        self.discovery_url = discovery_url
        self.direct_workers = direct_workers or []
        self.timeout = timeout

        self.workers: List[str] = []
        self.session_map: Dict[str, Union[str, List[str]]] = {}  # session_id -> worker_url(s)

        # 初始化时刷新 Worker 列表
        self.refresh_workers()

    def refresh_workers(self) -> List[str]:
        """
        刷新可用 Worker 列表

        Returns:
            Worker 地址列表
        """
        if self.direct_workers:
            self.workers = [self._normalize_url(w) for w in self.direct_workers]
            return self.workers

        if not self.discovery_url:
            logger.warning("No discovery URL or direct workers configured")
            return []

        try:
            resp = requests.get(self.discovery_url, timeout=self.timeout)
            resp.raise_for_status()
            addr_list = resp.json().get("ips", [])
            self.workers = [self._normalize_url(addr) for addr in addr_list]
            logger.info(f"Refreshed workers: {len(self.workers)} available")
        except Exception as e:
            logger.error(f"Failed to refresh workers: {e}")
            self.workers = []

        return self.workers

    def _normalize_url(self, addr: str) -> str:
        """标准化 URL"""
        if not addr.startswith("http"):
            return f"http://{addr}"
        return addr

    # ========================= Session Management =========================

    def create_sessions(
        self,
        batch_size: int,
        scenario: str = None,
        config: Dict[str, Any] = None,
        data_dir: str = None,
        dates_data: Dict[str, Dict[str, str]] = None,  # {date: {file_key: base64_content}}
    ) -> Dict[str, Any]:
        """
        批量创建会话

        Args:
            batch_size: 需要创建的会话数量
            scenario: 场景名称（单场景服务可省略）
            config: 环境配置
            data_dir: 数据目录（可选，自动扫描加载）
            dates_data: 预加载的日期数据（可选，优先级高于 data_dir）
                        格式: {date: {file_key: base64_content}}

        Returns:
            {"status": "created", "session_infos": {...}, "dates": [...]}
        """
        if not self.workers and not self.refresh_workers():
            raise Exception("No available workers found. Please check service registration.")

        # 确定实际可用的 Worker 数量
        actual_batch = min(batch_size, len(self.workers))
        if actual_batch < batch_size:
            logger.warning(
                f"Requested {batch_size} sessions but only {len(self.workers)} workers available. "
                f"Creating {actual_batch} sessions (others will be queued)."
            )

        # 加载数据：dates_data 优先，其次 data_dir 自动扫描
        if dates_data is None:
            dates_data = {}
        if not dates_data and data_dir:
            logger.info(f"Loading data from {data_dir}...")
            dates_data = self._load_all_dates(data_dir)
            logger.info(f"Loaded {len(dates_data)} dates: {list(dates_data.keys())}")

        # 创建 session -> worker 映射
        session_infos = {uuid.uuid4().hex: self.workers[i % len(self.workers)] for i in range(actual_batch)}

        # 并发创建会话
        session_infos = self._concurrent_create_sessions(session_infos, scenario, config, dates_data)

        self.session_map.update(session_infos)
        logger.info(f"Created {len(session_infos)} sessions on {len(set(session_infos.values()))} workers")

        return {
            "status": "created",
            "session_infos": session_infos,
            "dates": list(dates_data.keys()),
        }

    def _load_all_dates(self, data_dir: str) -> Dict[str, Dict[str, str]]:
        """
        加载数据目录下所有日期的数据

        Returns:
            {date: {file_name: base64_content}}
        """
        dates_data = {}

        for date_folder in os.listdir(data_dir):
            date_path = os.path.join(data_dir, date_folder)

            if not os.path.isdir(date_path) or date_folder.startswith("."):
                continue

            date_files = {}

            # 遍历日期目录下的所有文件
            for fname in os.listdir(date_path):
                if not fname.endswith(".csv"):
                    continue

                fpath = os.path.join(date_path, fname)
                if os.path.exists(fpath):
                    with open(fpath, "rb") as f:
                        content = f.read()
                        encoded = base64.b64encode(content).decode("utf-8")
                        # 使用文件名（不含扩展名）作为 key
                        key = fname.rsplit(".", 1)[0]
                        date_files[key] = encoded

            if date_files:
                dates_data[date_folder] = date_files

        return dates_data

    def _concurrent_create_sessions(
        self,
        session_infos: Dict[str, str],
        scenario: str,
        config: Dict[str, Any],
        dates_data: Dict[str, Dict[str, str]],
    ) -> Dict[str, str]:
        """并发创建会话"""

        @retry(max_retries=3, initial_delay=0.5, exceptions=(requests.RequestException,))
        def _create_single(worker_url: str, session_id: str):
            payload = {
                "session_id": session_id,
                "scenario": scenario,
                "config": config or {},
                "dates": dates_data,
            }

            resp = requests.post(
                f"{worker_url}/create",
                json=payload,
                timeout=60,  # 上传数据可能需要较长时间
            )
            resp.raise_for_status()
            return session_id, worker_url

        success_sessions = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(session_infos)) as executor:
            futures = {
                executor.submit(_create_single, worker_url, session_id): session_id
                for session_id, worker_url in session_infos.items()
            }
            for future in concurrent.futures.as_completed(futures):
                try:
                    session_id, worker_url = future.result()
                    success_sessions[session_id] = worker_url
                except Exception as e:
                    failed_sid = futures[future]
                    logger.error(f"Failed to create session {failed_sid}: {e}")

        return success_sessions

    # ========================= Batch Execution =========================

    def batch_step(
        self,
        actions: List[Any],
        serialize_fn: Callable[[Any], bytes] = None,
        deserialize_fn: Callable[[bytes], Any] = None,
    ) -> List[Any]:
        """
        批量执行 step

        实现队列调度：如果 action 数量大于 session 数量，会排队处理

        Args:
            actions: 动作列表
            serialize_fn: 序列化函数（默认使用 torch.save 或 pickle）
            deserialize_fn: 反序列化函数（默认使用 torch.load 或 pickle）

        Returns:
            结果列表，results[i] 对应 actions[i]
        """
        session_ids = list(self.session_map.keys())
        if not session_ids:
            raise Exception("No active sessions available for batch_step.")

        # 默认序列化/反序列化函数
        if serialize_fn is None:
            serialize_fn = self._default_serialize
        if deserialize_fn is None:
            deserialize_fn = self._default_deserialize

        # 工作队列
        work_queue: queue.SimpleQueue = queue.SimpleQueue()
        for i, action in enumerate(actions):
            work_queue.put((i, action))

        # 结果数组
        results: List[Any] = [None] * len(actions)
        results_lock = concurrent.futures.thread.threading.Lock()

        def run_session(session_id: str):
            """处理一个 session 的所有任务"""
            worker_url = self._get_session_worker(session_id)

            while True:
                try:
                    i, action = work_queue.get_nowait()
                except queue.Empty:
                    return

                try:
                    # 序列化 action
                    action_bytes = serialize_fn(action)

                    # 提交任务
                    task_id = self._submit_step(worker_url, session_id, action_bytes)

                    # 获取结果
                    result = self._get_step_result(worker_url, task_id, deserialize_fn)

                    with results_lock:
                        results[i] = result

                except Exception as e:
                    logger.error(f"Failed to process action {i} on session {session_id}: {e}")
                    with results_lock:
                        results[i] = None

        # 并发执行
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(session_ids)) as executor:
            list(executor.map(run_session, session_ids))

        return results

    def _get_session_worker(self, session_id: str) -> str:
        """获取 session 对应的 worker URL"""
        worker = self.session_map.get(session_id)
        if not worker:
            raise ValueError(f"Session {session_id} not found")
        if isinstance(worker, list):
            return worker[0]  # 如果有多个，返回第一个
        return worker

    @retry(max_retries=3, initial_delay=1.0, exceptions=(requests.RequestException,))
    def _submit_step(self, worker_url: str, session_id: str, action_bytes: bytes) -> str:
        """提交异步 step 任务"""
        files = {"action_tensor": ("action.pt", io.BytesIO(action_bytes))}
        resp = requests.post(
            f"{worker_url}/step/submit",
            data={"session_id": session_id},
            files=files,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()["task_id"]

    def _get_step_result(
        self,
        worker_url: str,
        task_id: str,
        deserialize_fn: Callable[[bytes], Any],
        poll_interval: float = 1.0,
        max_wait: float = 300.0,
    ) -> Any:
        """轮询获取异步 step 结果"""
        start_time = time.time()

        while time.time() - start_time < max_wait:
            try:
                resp = requests.get(
                    f"{worker_url}/step/result",
                    params={"task_id": task_id},
                    timeout=self.timeout,
                )
                resp.raise_for_status()

                content_type = resp.headers.get("content-type", "")

                if "application/octet-stream" in content_type:
                    # 二进制结果，反序列化
                    return deserialize_fn(resp.content)

                data = resp.json()
                status = data.get("status")

                if status == "completed":
                    return data.get("result")
                elif status == "failed":
                    raise Exception(f"Task failed: {data.get('error')}")
                elif status == "running":
                    time.sleep(poll_interval)
                    # 指数退避
                    poll_interval = min(poll_interval * 1.5, 10.0)
                else:
                    time.sleep(poll_interval)

            except requests.RequestException as e:
                logger.warning(f"Error polling result from {worker_url}: {e}")
                time.sleep(poll_interval)

        raise TimeoutError(f"Task {task_id} timed out after {max_wait}s")

    def _default_serialize(self, obj: Any) -> bytes:
        """默认序列化"""
        buffer = io.BytesIO()
        try:
            import torch

            torch.save(obj, buffer)
        except ImportError:
            import pickle

            pickle.dump(obj, buffer)
        return buffer.getvalue()

    def _default_deserialize(self, data: bytes) -> Any:
        """默认反序列化"""
        buffer = io.BytesIO(data)
        try:
            import torch

            return torch.load(buffer, weights_only=False)
        except ImportError:
            import pickle

            return pickle.load(buffer)

    # ========================= Cleanup =========================

    def close(self):
        """关闭所有会话"""
        if not self.session_map:
            return

        def _close_single(session_id: str, worker_url: str):
            try:
                requests.post(
                    f"{worker_url}/close",
                    json={"session_id": session_id},
                    timeout=5,
                )
            except Exception as e:
                logger.warning(f"Failed to close session {session_id}: {e}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.session_map)) as executor:
            futures = [executor.submit(_close_single, sid, url) for sid, url in self.session_map.items()]
            concurrent.futures.wait(futures)

        self.session_map.clear()
        logger.info("All sessions closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ========================= Convenience Functions =========================


def create_sdk(
    discovery_url: str = None,
    workers: List[str] = None,
) -> SimulationSDK:
    """
    创建 SDK 实例的便捷函数

    Args:
        discovery_url: 服务发现 URL
        workers: 直接指定的 Worker 列表

    Returns:
        SimulationSDK 实例
    """
    return SimulationSDK(
        discovery_url=discovery_url,
        direct_workers=workers,
    )
