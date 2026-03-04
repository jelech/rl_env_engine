"""
异步任务管理器 - 处理长时间运行的仿真任务
"""

import os
import uuid
import time
import asyncio
import logging
import threading
from enum import Enum
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass, field
from multiprocessing import Process, Queue
from threading import Semaphore
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """任务信息"""

    task_id: str
    status: TaskStatus
    created_at: float = field(default_factory=time.time)
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def _process_wrapper_func(queue, fn, a, kw):
    try:
        result = fn(*a, **kw)
        queue.put({"status": "success", "result": result})
    except Exception as e:
        import traceback

        queue.put(
            {
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
        )


class TaskManager:
    """
    异步任务管理器

    支持：
    - 异步任务提交和状态查询
    - 并发控制（通过 Semaphore 限制）
    - 进程隔离执行（可选，用于内存隔离）
    """

    def __init__(
        self,
        max_concurrent: int = 2,
        use_process_isolation: bool = False,
    ):
        """
        初始化任务管理器

        Args:
            max_concurrent: 最大并发任务数
            use_process_isolation: 是否使用进程隔离（每个任务在独立进程中运行）
        """
        self.max_concurrent = max_concurrent
        self.use_process_isolation = use_process_isolation
        self._tasks: Dict[str, Task] = {}
        self._semaphore = Semaphore(max_concurrent)
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent * 2)
        self._lock = threading.Lock()

    def create_task(self, metadata: Dict[str, Any] = None) -> str:
        """
        创建新任务

        Args:
            metadata: 任务元数据

        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            status=TaskStatus.PENDING,
            metadata=metadata or {},
        )

        with self._lock:
            self._tasks[task_id] = task

        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务信息"""
        return self._tasks.get(task_id)

    def update_task(
        self,
        task_id: str,
        status: TaskStatus = None,
        result: Any = None,
        error: str = None,
    ):
        """更新任务状态"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                if status:
                    task.status = status
                if result is not None:
                    task.result = result
                if error is not None:
                    task.error = error

    async def submit_async(
        self,
        func: Callable,
        *args,
        task_id: str = None,
        **kwargs,
    ) -> str:
        """
        异步提交任务

        Args:
            func: 要执行的函数
            *args: 位置参数
            task_id: 可选的任务ID（如果不提供会自动生成）
            **kwargs: 关键字参数

        Returns:
            任务ID
        """
        if task_id is None:
            task_id = self.create_task()

        self.update_task(task_id, status=TaskStatus.RUNNING)

        # 在事件循环中异步执行
        asyncio.create_task(self._run_task(task_id, func, *args, **kwargs))

        return task_id

    async def _run_task(
        self,
        task_id: str,
        func: Callable,
        *args,
        **kwargs,
    ):
        """在后台运行任务"""
        loop = asyncio.get_running_loop()

        if self.use_process_isolation:
            # 使用进程隔离
            await loop.run_in_executor(
                None,
                self._run_in_process,
                task_id,
                func,
                args,
                kwargs,
            )
        else:
            # 在线程池中运行
            await loop.run_in_executor(
                self._executor,
                self._run_in_thread,
                task_id,
                func,
                args,
                kwargs,
            )

    def _run_in_thread(
        self,
        task_id: str,
        func: Callable,
        args: tuple,
        kwargs: dict,
    ):
        """在线程中运行任务"""
        self._semaphore.acquire()
        try:
            result = func(*args, **kwargs)
            self.update_task(task_id, status=TaskStatus.COMPLETED, result=result)
        except Exception as e:
            import traceback

            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            logger.error(f"Task {task_id} failed: {error_msg}")
            self.update_task(task_id, status=TaskStatus.FAILED, error=str(e))
        finally:
            self._semaphore.release()

    def _run_in_process(
        self,
        task_id: str,
        func: Callable,
        args: tuple,
        kwargs: dict,
    ):
        """在独立进程中运行任务（用于内存隔离）"""
        self._semaphore.acquire()
        try:
            result_queue = Queue()

            p = Process(
                target=_process_wrapper_func,
                args=(result_queue, func, args, kwargs),
            )
            p.start()
            logger.info(f"Task {task_id}: Started in process PID={p.pid}")

            p.join()
            logger.info(f"Task {task_id}: Process exited")

            # 获取结果
            result_data = result_queue.get()

            if result_data["status"] == "success":
                self.update_task(
                    task_id,
                    status=TaskStatus.COMPLETED,
                    result=result_data["result"],
                )
            else:
                self.update_task(
                    task_id,
                    status=TaskStatus.FAILED,
                    error=result_data["error"],
                )

        except Exception as e:
            import traceback

            logger.error(f"Task {task_id} process error: {traceback.format_exc()}")
            self.update_task(task_id, status=TaskStatus.FAILED, error=str(e))
        finally:
            self._semaphore.release()

    def cleanup_old_tasks(self, max_age_seconds: int = 3600):
        """清理过期任务"""
        current_time = time.time()
        with self._lock:
            expired = [
                tid
                for tid, task in self._tasks.items()
                if current_time - task.created_at > max_age_seconds
                and task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
            ]
            for tid in expired:
                del self._tasks[tid]

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired tasks")

    def shutdown(self):
        """关闭任务管理器"""
        self._executor.shutdown(wait=True)
