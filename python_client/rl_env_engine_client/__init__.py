"""rl_env_engine_client

Python gRPC client + SB3 gymnasium wrapper for the Go rl_env_engine project.

Install (from repo root):
    pip install "git+https://github.com/jelech/rl_env_engine.git#subdirectory=python_client"

With RL extras:
    pip install "git+https://github.com/jelech/rl_env_engine.git#subdirectory=python_client&egg=rl-env-engine-client[rl]"

After installation:
    from rl_env_engine_client.sb3_simple_env import SB3GrpcSimpleEnv
"""

__all__ = [
    "SB3GrpcSimpleEnv",
    "SimulationGrpcClient",
]

__version__ = "0.1.0"

# 重新导出核心类
from .sb3_simple_env import SB3GrpcSimpleEnv  # noqa: E402
from .grpc_client import SimulationGrpcClient  # noqa: E402
