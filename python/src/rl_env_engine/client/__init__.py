"""RL Env Engine Client SDK

提供多种客户端接入方式：
- GrpcEnv: Gymnasium 兼容的 gRPC 环境包装器
- LocalEnv: 本地 Go 共享库环境
- SimulationGrpcClient: 低级 gRPC 客户端
- SimulationSDK: 高级 SDK，支持服务发现和批量执行（HTTP 分布式）
- InProcessSDK: 进程内批量 SDK，支持 Python/Cython/C 环境（本地高性能）
- CEnvAdapter: C 共享库环境适配器
"""

# from rl_env_engine.client.grpc_env import GrpcEnv
# from rl_env_engine.client.local_env import LocalEnv
# from rl_env_engine.client.grpc_client import SimulationGrpcClient
from rl_env_engine.client.sdk import SimulationSDK, create_sdk
from rl_env_engine.client.inprocess_sdk import InProcessSDK, CEnvAdapter

__all__ = [
    "GrpcEnv",
    "LocalEnv",
    "SimulationGrpcClient",
    "SimulationSDK",
    "create_sdk",
    "InProcessSDK",
    "CEnvAdapter",
]
