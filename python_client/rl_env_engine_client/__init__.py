"""rl_env_engine_client

通用gRPC环境客户端包，为仿真引擎提供标准化的强化学习环境接口。

本地安装（从仓库根目录）:
    pip install -e python_client

或安装RL扩展依赖:
    pip install -e "python_client[rl]"

使用示例:
    from rl_env_engine_client import GrpcEnv
"""

__all__ = [
    "GrpcEnv",
    "SimulationGrpcClient",
]

__version__ = "0.1.0"

from .grpc_env import GrpcEnv  # noqa: E402
from .grpc_client import SimulationGrpcClient  # noqa: E402
