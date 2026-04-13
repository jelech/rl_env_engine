"""rl_env_engine

Python SDK for RL Env Engine - 支持 gRPC 和 HTTP 两种协议的强化学习环境框架。

Installation:
    pip install rl-env-engine

Or with RL dependencies:
    pip install rl-env-engine[rl]

Client Usage:
    from rl_env_engine.client import GrpcEnv, SimulationSDK

    # Gymnasium 风格
    env = GrpcEnv(scenario="cartpole", host="127.0.0.1", port=9090)
    obs, info = env.reset()

    # 批量执行风格（支持服务发现）
    sdk = SimulationSDK(discovery_url="http://localhost:8000/ips")
    sdk.create_sessions(batch_size=4, scenario="my_scenario")
    results = sdk.batch_step(actions)
    sdk.close()

Server Usage:
    from rl_env_engine.server import create_app, BaseScenario, run_server

    class MyScenario(BaseScenario):
        @property
        def name(self): return "my_scenario"
        def create_environment(self, config): ...
        def reset(self, env, **kwargs): ...
        def step(self, env, action, **kwargs): ...

    app = create_app([MyScenario()])
    run_server(app, port=8000)
"""

__version__ = "0.3.0"

# Client SDK
from rl_env_engine.client import (
    # GrpcEnv,
    # LocalEnv,
    # SimulationGrpcClient,
    SimulationSDK,
    create_sdk,
)

__all__ = [
    # Client
    "GrpcEnv",
    "LocalEnv",
    "SimulationGrpcClient",
    "SimulationSDK",
    "create_sdk",
]

# Server SDK (optional import - requires fastapi)
try:
    from rl_env_engine.server import (
        create_app,
        BaseScenario,
        ServiceDiscovery,
        TaskManager,
    )

    __all__.extend(
        [
            "create_app",
            "BaseScenario",
            "ServiceDiscovery",
            "TaskManager",
        ]
    )
except ImportError:
    # FastAPI not installed, server SDK not available
    pass
