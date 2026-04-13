"""
InProcess SDK - 进程内直接执行环境，零网络开销。

适用场景:
- 单机训练，CPU 资源充足，规模不大
- 不需要分布式仿真集群
- 追求最低延迟和最高吞吐

支持三种业务环境实现:
1. Python: 任意 Python 类，实现 reset()/step()/close()
2. Cython: 编译的 .pyx 模块，cpdef 方法提供近 C 性能
3. C: 共享库 (.so/.dylib)，通过 CEnvAdapter 桥接

并行模式:
- "sequential": 顺序执行（默认，最简单，适合调试）
- "thread": 线程并行（适用于释放 GIL 的 Cython/C 环境）
- "subprocess": 子进程并行（适用于纯 Python CPU 密集型环境，绕过 GIL）

与 SimulationSDK 保持兼容的 API，便于在本地开发和分布式部署间切换。
"""

import os
import uuid
import json
import queue
import ctypes
import logging
import multiprocessing as mp
import concurrent.futures
import numpy as np
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class InProcessSDK:
    """
    进程内批量环境 SDK。

    用法:
        # Python/Cython 环境
        sdk = InProcessSDK(MyEnvClass, num_envs=4, parallel="thread")
        sdk.create_sessions(config={"param": 1.0})
        results = sdk.batch_step(actions)
        sdk.close()

        # C 共享库
        sdk = InProcessSDK.from_c_lib("libmyenv.so", num_envs=4)
    """

    def __init__(
        self,
        env_factory: Union[type, Callable[..., Any]],
        num_envs: int = 1,
        parallel: str = "sequential",
    ):
        """
        Args:
            env_factory: 环境工厂。可以是类（自动 config= 传参）或
                         callable(config_dict) -> env_instance。
                         环境实例必须实现:
                           reset(**kw)  -> (obs, info)
                           step(action) -> (obs, reward, done, truncated, info)
                           close()
            num_envs: 环境数量
            parallel: "sequential" | "thread" | "subprocess"
        """
        self.env_factory = env_factory
        self.num_envs = num_envs
        self.parallel = parallel

        self.envs: List[Any] = []
        self.session_map: Dict[str, int] = {}
        self._workers: List["_SubprocessEnvWorker"] = []

    @property
    def _is_subprocess(self) -> bool:
        return self.parallel == "subprocess"

    # ========================= Session Management =========================

    def create_sessions(
        self,
        batch_size: int = None,
        config: Dict[str, Any] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        创建环境实例（对标 SimulationSDK.create_sessions）。

        Args:
            batch_size: 环境数量，默认 num_envs
            config: 传递给 env_factory 的配置
        """
        if self.envs or self._workers:
            self.close()

        batch_size = batch_size or self.num_envs
        session_ids = []

        if self._is_subprocess:
            for i in range(batch_size):
                worker = _SubprocessEnvWorker(self.env_factory, config, **kwargs)
                self._workers.append(worker)
                sid = uuid.uuid4().hex
                self.session_map[sid] = i
                session_ids.append(sid)
        else:
            for i in range(batch_size):
                env = self._make_env(config, **kwargs)
                self.envs.append(env)
                sid = uuid.uuid4().hex
                self.session_map[sid] = i
                session_ids.append(sid)

        logger.info(
            f"Created {batch_size} in-process environments (parallel={self.parallel})"
        )
        return {
            "status": "created",
            "session_ids": session_ids,
            "num_envs": batch_size,
        }

    def _make_env(self, config: Dict = None, **kwargs) -> Any:
        if isinstance(self.env_factory, type):
            return self.env_factory(config=config or {}, **kwargs)
        return self.env_factory(config or {}, **kwargs)

    # ========================= Batch Operations =========================

    def batch_reset(self, **kwargs) -> List[Any]:
        """重置所有环境，返回 [(obs, info), ...] 列表。"""
        if self._is_subprocess:
            return [w.reset(**kwargs) for w in self._workers]

        if self.parallel == "thread":
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=len(self.envs)
            ) as pool:
                futures = [pool.submit(env.reset, **kwargs) for env in self.envs]
                return [f.result() for f in futures]

        return [env.reset(**kwargs) for env in self.envs]

    def batch_step(
        self,
        actions: List[Any],
        serialize_fn: Callable = None,
        deserialize_fn: Callable = None,
    ) -> List[Any]:
        """
        批量执行 step（对标 SimulationSDK.batch_step）。

        支持队列调度: len(actions) > num_envs 时自动排队复用。
        serialize_fn / deserialize_fn 参数仅为 API 兼容，进程内无需序列化。

        Returns:
            results[i] 对应 actions[i] 的 step 返回值
        """
        envs = self._workers if self._is_subprocess else self.envs
        n_envs = len(envs)

        if not envs:
            raise RuntimeError("No active environments. Call create_sessions() first.")
        if not actions:
            return []

        if len(actions) <= n_envs:
            return self._parallel_step(envs[: len(actions)], actions)

        # 队列调度: actions 多于 envs
        results: List[Any] = [None] * len(actions)
        work_queue: queue.SimpleQueue = queue.SimpleQueue()
        for i, action in enumerate(actions):
            work_queue.put((i, action))

        lock = concurrent.futures.thread.threading.Lock()

        def _run_env(env):
            while True:
                try:
                    i, action = work_queue.get_nowait()
                except queue.Empty:
                    return
                result = env.step(action)
                with lock:
                    results[i] = result

        if self.parallel == "thread":
            with concurrent.futures.ThreadPoolExecutor(max_workers=n_envs) as pool:
                list(pool.map(_run_env, envs))
        else:
            for env in envs:
                _run_env(env)

        return results

    def _parallel_step(
        self, envs: List[Any], actions: List[Any]
    ) -> List[Any]:
        if self.parallel == "thread" and not self._is_subprocess:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=len(envs)
            ) as pool:
                futures = [
                    pool.submit(env.step, action)
                    for env, action in zip(envs, actions)
                ]
                return [f.result() for f in futures]

        return [env.step(action) for env, action in zip(envs, actions)]

    # ========================= Cleanup =========================

    def close(self):
        for env in self.envs:
            try:
                env.close()
            except Exception as e:
                logger.warning(f"Error closing env: {e}")
        self.envs.clear()

        for w in self._workers:
            try:
                w.close()
            except Exception as e:
                logger.warning(f"Error closing subprocess worker: {e}")
        self._workers.clear()

        self.session_map.clear()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ========================= Factory Helpers =========================

    @staticmethod
    def from_c_lib(
        lib_path: str,
        num_envs: int = 1,
        parallel: str = "thread",
    ) -> "InProcessSDK":
        """
        从 C 共享库创建 SDK。

        共享库需实现 env_interface.h 中定义的标准 C 接口。
        C 环境天然释放 GIL，推荐 parallel="thread"。

        Args:
            lib_path: .so / .dylib 路径
            num_envs: 环境数量
            parallel: 并行模式
        """
        factory = _CEnvFactory(lib_path)
        return InProcessSDK(
            env_factory=factory,
            num_envs=num_envs,
            parallel=parallel,
        )


# ========================= Subprocess Worker =========================


class _SubprocessEnvWorker:
    """在独立子进程中运行环境实例，通过 Pipe 通信。"""

    def __init__(self, env_factory, config, **kwargs):
        self.parent_conn, child_conn = mp.Pipe()
        self.process = mp.Process(
            target=self._worker_loop,
            args=(env_factory, config, kwargs, child_conn),
            daemon=True,
        )
        self.process.start()
        child_conn.close()

    @staticmethod
    def _worker_loop(env_factory, config, kwargs, conn):
        if isinstance(env_factory, type):
            env = env_factory(config=config or {}, **kwargs)
        else:
            env = env_factory(config or {}, **kwargs)

        try:
            while True:
                msg = conn.recv()
                cmd = msg[0]
                if cmd == "step":
                    conn.send(env.step(msg[1]))
                elif cmd == "reset":
                    kw = msg[1] if len(msg) > 1 else {}
                    conn.send(env.reset(**kw))
                elif cmd == "close":
                    env.close()
                    conn.send(None)
                    break
        except (EOFError, BrokenPipeError):
            try:
                env.close()
            except Exception:
                pass

    def step(self, action):
        self.parent_conn.send(("step", action))
        return self.parent_conn.recv()

    def reset(self, **kwargs):
        self.parent_conn.send(("reset", kwargs))
        return self.parent_conn.recv()

    def close(self):
        try:
            self.parent_conn.send(("close",))
            self.parent_conn.recv()
        except Exception:
            pass
        self.process.join(timeout=5)
        if self.process.is_alive():
            self.process.kill()


# ========================= C Shared Library Adapter =========================


class _CEnvFactory:
    """可 pickle 的 CEnvAdapter 工厂（用于 subprocess 模式）。"""

    def __init__(self, lib_path: str):
        self.lib_path = lib_path

    def __call__(self, config: Dict = None):
        return CEnvAdapter(self.lib_path, config)


class CEnvAdapter:
    """
    C 共享库环境适配器。

    将实现了 env_interface.h 标准接口的 .so/.dylib 包装为 Python 环境对象，
    提供 reset() / step() / close() 方法，可直接用于 InProcessSDK。

    标准 C 接口:
        void*  env_create(const char* config_json);
        int    env_reset(void* handle, double* obs_out, int max_len);
        int    env_step(void* handle, const double* action, int action_len,
                        double* obs_out, int max_obs,
                        double* reward_out, int* done_out);
        void   env_close(void* handle);
        int    env_obs_size(void* handle);    // optional
        int    env_action_size(void* handle); // optional
    """

    def __init__(self, lib_path: str, config: Dict[str, Any] = None):
        if not os.path.exists(lib_path):
            raise FileNotFoundError(f"Shared library not found: {lib_path}")

        self.lib = ctypes.CDLL(lib_path)
        self._setup_signatures()

        config_json = json.dumps(config or {}).encode("utf-8")
        self.handle = self.lib.env_create(config_json)
        if not self.handle:
            raise RuntimeError(
                f"env_create returned NULL for config: {config}"
            )

        self._obs_size = self._get_size("env_obs_size", 64)
        self._act_size = self._get_size("env_action_size", 1)
        buf_size = max(self._obs_size * 4, 4096)
        self._obs_buf = (ctypes.c_double * buf_size)()
        self._buf_len = buf_size
        self._reward = ctypes.c_double(0.0)
        self._done = ctypes.c_int(0)

    def _setup_signatures(self):
        self.lib.env_create.argtypes = [ctypes.c_char_p]
        self.lib.env_create.restype = ctypes.c_void_p

        self.lib.env_reset.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int,
        ]
        self.lib.env_reset.restype = ctypes.c_int

        self.lib.env_step.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_int),
        ]
        self.lib.env_step.restype = ctypes.c_int

        self.lib.env_close.argtypes = [ctypes.c_void_p]
        self.lib.env_close.restype = None

    def _get_size(self, func_name: str, default: int) -> int:
        try:
            fn = getattr(self.lib, func_name)
            fn.argtypes = [ctypes.c_void_p]
            fn.restype = ctypes.c_int
            return fn(self.handle)
        except AttributeError:
            return default

    def reset(self, **kwargs) -> Tuple[np.ndarray, dict]:
        obs_len = self.lib.env_reset(self.handle, self._obs_buf, self._buf_len)
        if obs_len < 0:
            raise RuntimeError(f"env_reset failed with code {obs_len}")
        obs = np.frombuffer(
            (ctypes.c_double * obs_len).from_address(
                ctypes.addressof(self._obs_buf)
            ),
            dtype=np.float64,
        ).copy()
        return obs, {}

    def step(
        self, action: Any
    ) -> Tuple[np.ndarray, float, bool, bool, dict]:
        if isinstance(action, (int, float)):
            action = [float(action)]
        elif isinstance(action, np.ndarray):
            action = action.astype(np.float64).flatten().tolist()
        elif isinstance(action, (list, tuple)):
            action = [float(a) for a in action]

        c_action = (ctypes.c_double * len(action))(*action)

        obs_len = self.lib.env_step(
            self.handle,
            c_action,
            len(action),
            self._obs_buf,
            self._buf_len,
            ctypes.byref(self._reward),
            ctypes.byref(self._done),
        )
        if obs_len < 0:
            raise RuntimeError(f"env_step failed with code {obs_len}")

        obs = np.frombuffer(
            (ctypes.c_double * obs_len).from_address(
                ctypes.addressof(self._obs_buf)
            ),
            dtype=np.float64,
        ).copy()
        return obs, self._reward.value, bool(self._done.value), False, {}

    def close(self):
        if hasattr(self, "handle") and self.handle:
            self.lib.env_close(self.handle)
            self.handle = None
