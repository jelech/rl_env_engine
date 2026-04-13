"""
FastAPI 服务器框架 - 提供标准的环境服务接口

基于 RL4SCS/envs/br_driver_allocation/api.py 的模式设计
"""

import os
import io
import sys
import shutil
import tempfile
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from contextlib import asynccontextmanager
from loguru import logger
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .discovery import ServiceDiscovery
from .task_manager import TaskManager, TaskStatus


# ========================= Request/Response Models =========================


class CreateSessionRequest(BaseModel):
    """创建会话请求"""

    session_id: str
    scenario: Optional[str] = None  # 可选：单场景服务可省略
    config: Optional[Dict[str, Any]] = None
    # 支持多日期数据（用于批量仿真）
    dates: Optional[Dict[str, Dict[str, str]]] = None  # {date: {file_name: base64_data}}


class CloseSessionRequest(BaseModel):
    """关闭会话请求"""

    session_id: str


class ResetRequest(BaseModel):
    """重置环境请求"""

    session_id: str
    date: Optional[str] = None  # 可选：指定日期


class StepRequest(BaseModel):
    """步进请求（同步）"""

    session_id: str
    action: Dict[str, Any]


# ========================= Base Scenario =========================


class BaseScenario(ABC):
    """
    场景基类 - 用户需要继承此类实现自己的仿真逻辑
    """

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def create_environment(self, config: Dict[str, Any]) -> Any:
        pass

    @abstractmethod
    def reset(self, env: Any, **kwargs) -> Dict[str, Any]:
        pass

    @abstractmethod
    def step(self, env: Any, action: Any, **kwargs) -> Dict[str, Any]:
        pass

    def close(self, env: Any):
        """关闭环境（可选实现）"""
        pass


# ========================= Session Manager =========================


class SessionManager:
    """会话管理器"""

    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def create(
        self,
        session_id: str,
        scenario: BaseScenario,
        config: Dict[str, Any] = None,
        dates_data: Dict[str, Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """创建会话"""
        # 清理旧会话
        if session_id in self.sessions:
            self.close(session_id)

        # 创建临时目录（用于存储文件）
        temp_dir = tempfile.mkdtemp(prefix=f"session_{session_id}_")

        # 处理日期数据（如果有）
        dates = {}
        if dates_data:
            import base64

            for date, files_data in dates_data.items():
                date_dir = os.path.join(temp_dir, date)
                os.makedirs(date_dir, exist_ok=True)

                date_files = {}
                for file_name, file_content in files_data.items():
                    content = base64.b64decode(file_content)
                    file_path = os.path.join(date_dir, f"{file_name}.csv")
                    with open(file_path, "wb") as f:
                        f.write(content)
                    date_files[file_name] = file_path

                dates[date] = date_files

        # 创建环境
        env = scenario.create_environment(config or {})

        session_data = {
            "scenario": scenario,
            "env": env,
            "config": config or {},
            "temp_dir": temp_dir,
            "dates": dates,
        }

        self.sessions[session_id] = session_data
        logger.info(f"Session {session_id} created with scenario {scenario.name}")

        return {
            "status": "created",
            "session_id": session_id,
            "dates": list(dates.keys()) if dates else [],
        }

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话"""
        return self.sessions.get(session_id)

    def close(self, session_id: str) -> bool:
        """关闭会话"""
        session = self.sessions.pop(session_id, None)
        if session:
            # 关闭环境
            try:
                session["scenario"].close(session["env"])
            except Exception as e:
                logger.warning(f"Error closing environment: {e}")

            # 清理临时目录
            try:
                shutil.rmtree(session["temp_dir"], ignore_errors=True)
            except Exception as e:
                logger.warning(f"Error cleaning temp dir: {e}")

            logger.info(f"Session {session_id} closed")
            return True
        return False

    def list_sessions(self) -> List[str]:
        """列出所有会话"""
        return list(self.sessions.keys())


# ========================= Create App Factory =========================


def _run_step_task(
    scenario: BaseScenario,
    env: Any,
    action: Any,
    date: Optional[str] = None,
    date_data: Optional[Dict] = None,
) -> Any:
    """
    步进任务执行函数（顶层定义以支持 pickle）
    """
    kwargs = {}
    if date:
        kwargs["date"] = date
        kwargs["date_data"] = date_data
    return scenario.step(env, action, **kwargs)


def create_app(
    scenarios: List[BaseScenario],
    scenario_name: str = "rl_env_engine",
    enable_discovery: bool = True,
    max_concurrent_tasks: int = 2,
    use_process_isolation: bool = False,
) -> FastAPI:
    """
    创建 FastAPI 应用

    Args:
        scenarios: 场景列表
        scenario_name: 服务名称（用于服务发现）
        enable_discovery: 是否启用服务发现
        max_concurrent_tasks: 最大并发任务数
        use_process_isolation: 是否使用进程隔离

    Returns:
        FastAPI 应用实例
    """
    # ========================= Lifecycle Events =========================

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        if discovery:
            port = int(os.getenv("PORT", 8000))
            discovery.register(port)
            logger.info(f"Service discovery enabled, registered on port {port}")

        yield

        # Shutdown
        if discovery:
            discovery.unregister()
        task_manager.shutdown()
        # 关闭所有会话
        for sid in list(session_manager.sessions.keys()):
            session_manager.close(sid)

    app = FastAPI(title=f"RL Env Engine - {scenario_name}", lifespan=lifespan)

    logger.remove()
    logger.add(sys.stderr, level="INFO")
    log_dir = os.getenv("LOG_DIR", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"server_{scenario_name}_{{time:YYYY-MM-DD}}.log")

    logger.add(
        log_file,
        rotation="100 MB",  # 100MB 滚动一次
        retention="10 days",  # 保留 10 天
        compression="zip",  # 压缩旧日志
        enqueue=True,  # 异步写入，线程安全
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{line} - {message}",
    )

    # 场景注册表
    scenario_registry: Dict[str, BaseScenario] = {s.name: s for s in scenarios}

    # 会话管理器
    session_manager = SessionManager()

    # 任务管理器
    task_manager = TaskManager(
        max_concurrent=max_concurrent_tasks,
        use_process_isolation=use_process_isolation,
    )

    # 服务发现（可选）
    discovery: Optional[ServiceDiscovery] = None
    if enable_discovery:
        discovery = ServiceDiscovery(scenario_name=scenario_name)

    # ========================= API Endpoints =========================

    @app.get("/")
    async def index():
        """API 信息"""
        return {
            "name": f"RL Env Engine - {scenario_name}",
            "version": "1.0.0",
            "scenarios": list(scenario_registry.keys()),
            "endpoints": {
                "GET /": "API information",
                "GET /ips": "Get available workers",
                "GET /info": "Get service info",
                "POST /create": "Create session",
                "POST /reset": "Reset environment",
                "POST /step": "Step environment (sync)",
                "POST /step/submit": "Submit async step",
                "GET /step/result": "Get async step result",
                "POST /close": "Close session",
            },
        }

    @app.get("/ips")
    async def get_ips():
        """获取所有存活的 Worker（用于服务发现）"""
        if discovery:
            ips = discovery.get_services()
            return {"ips": ips}
        return {"ips": [], "message": "Service discovery not enabled"}

    @app.get("/info")
    async def get_info():
        """获取服务信息"""
        return {
            "scenarios": list(scenario_registry.keys()),
            "sessions": session_manager.list_sessions(),
            "active_sessions": len(session_manager.sessions),
        }

    @app.post("/create")
    async def create_session(request: CreateSessionRequest):
        """创建会话"""
        # scenario 字段可选：单场景服务自动推断
        scenario_key = request.scenario
        if not scenario_key:
            if len(scenario_registry) == 1:
                scenario_key = next(iter(scenario_registry))
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Multiple scenarios available, please specify one: {list(scenario_registry.keys())}",
                )

        scenario = scenario_registry.get(scenario_key)
        if not scenario:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown scenario: {scenario_key}. Available: {list(scenario_registry.keys())}",
            )

        try:
            result = session_manager.create(
                session_id=request.session_id,
                scenario=scenario,
                config=request.config,
                dates_data=request.dates,
            )
            return result
        except Exception as e:
            logger.exception(f"Failed to create session: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/reset")
    async def reset_environment(request: ResetRequest):
        """重置环境"""
        session = session_manager.get(request.session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {request.session_id} not found",
            )

        try:
            scenario: BaseScenario = session["scenario"]
            env = session["env"]

            # 构建额外参数
            kwargs = {}
            if request.date:
                kwargs["date"] = request.date
                kwargs["date_data"] = session["dates"].get(request.date, {})

            result = scenario.reset(env, **kwargs)
            return result
        except Exception as e:
            logger.exception(f"Failed to reset environment: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/step")
    async def step_environment(request: StepRequest):
        """同步步进环境"""
        session = session_manager.get(request.session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {request.session_id} not found",
            )

        try:
            scenario: BaseScenario = session["scenario"]
            env = session["env"]

            # 从 action 中提取 date 信息，传递 date_data
            kwargs = {}
            action = request.action
            if isinstance(action, dict) and "date" in action:
                date = action["date"]
                kwargs["date"] = date
                kwargs["date_data"] = session["dates"].get(date, {})

            result = scenario.step(env, action, **kwargs)
            return result
        except Exception as e:
            logger.exception(f"Failed to step environment: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/step/submit")
    async def submit_step(
        session_id: str = Form(...),
        action_tensor: UploadFile = File(...),
    ):
        """
        提交异步步进任务

        用于长时间运行的仿真任务
        """
        session = session_manager.get(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found",
            )

        try:
            # 读取 action
            action_bytes = await action_tensor.read()

            # 尝试解析为 torch tensor 或普通数据
            try:
                import torch

                action = torch.load(io.BytesIO(action_bytes), weights_only=False)
            except Exception:
                import pickle

                action = pickle.loads(action_bytes)

            # 提取日期（如果 action 是字典）
            date = None
            if isinstance(action, dict):
                date = action.get("date")

            # 创建任务
            task_id = task_manager.create_task(metadata={"session_id": session_id, "date": date})

            # 异步提交
            await task_manager.submit_async(
                _run_step_task,
                scenario=session["scenario"],
                env=session["env"],
                action=action,
                date=date,
                date_data=session["dates"].get(date, {}) if date else None,
                task_id=task_id,
            )

            return {"status": "submitted", "task_id": task_id, "date": date}

        except Exception as e:
            logger.exception(f"Failed to submit step: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/step/result")
    async def get_step_result(task_id: str):
        """获取异步步进结果"""
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if task.status == TaskStatus.RUNNING:
            return {"status": "running"}

        if task.status == TaskStatus.FAILED:
            return {"status": "failed", "error": task.error}

        if task.status == TaskStatus.COMPLETED:
            result = task.result

            # 如果结果包含 tensor，序列化返回
            try:
                import torch

                if isinstance(result, torch.Tensor):
                    buffer = io.BytesIO()
                    torch.save(result, buffer)
                    buffer.seek(0)
                    return StreamingResponse(
                        buffer,
                        media_type="application/octet-stream",
                        headers={"X-Task-Status": "completed"},
                    )
            except ImportError:
                pass

            # 返回 JSON
            return {"status": "completed", "result": result}

        return {"status": str(task.status)}

    @app.post("/close")
    async def close_session(request: CloseSessionRequest):
        """关闭会话"""
        if session_manager.close(request.session_id):
            return {"status": "closed", "session_id": request.session_id}
        return {"status": "not_found", "message": "Session not found or already closed"}

    return app


# ========================= Helper to Run Server =========================


def run_server(
    app: FastAPI,
    host: str = "0.0.0.0",
    port: int = None,
):
    """
    运行服务器

    Args:
        app: FastAPI 应用
        host: 绑定地址
        port: 端口（默认从环境变量 PORT 读取，否则 8000）
    """
    import uvicorn

    if port is None:
        port = int(os.getenv("PORT", 8000))

    uvicorn.run(app, host=host, port=port)
