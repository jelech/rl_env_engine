# RL Env Engine

A flexible simulation framework for reinforcement learning with multi-language SDK support.

## Project Structure

```
rl_env_engine/
├── api/proto/v1/                 # Protocol definitions (source of truth)
│   ├── simulation.proto          # SimulationService
│   ├── collector.proto           # CollectorService + Trajectory
│   └── weightsync.proto          # WeightSyncService
│
├── go/                           # Go module
│   ├── cmd/server/               # gRPC server entry point
│   ├── internal/
│   │   ├── server/               # gRPC server (keepalive + msg size 配置)
│   │   └── scenarios/            # 内置场景 (simple, cartpole)
│   └── pkg/
│       ├── api/v1/               # Generated protobuf code
│       ├── client/               # Go Client SDK
│       ├── collector/            # Collector driver + SKU 分配策略
│       ├── core/                 # 核心接口 + Trajectory 对象池
│       └── weightsync/           # Redis 权重同步器
│
├── python/src/rl_env_engine/     # Python package
│   ├── client/                   # GrpcEnv, LocalEnv, SimulationSDK
│   ├── server/                   # FastAPI Server, TaskManager
│   ├── learner/                  # 训练框架
│   │   ├── models.py             # PolicyNetwork + ValueNetwork
│   │   ├── ppo.py                # PPO 算法
│   │   ├── buffer.py             # RolloutBuffer + GAE
│   │   ├── distributed.py        # DDP 训练上下文
│   │   ├── trainer.py            # 训练主循环
│   │   ├── model_factory.py      # Checkpoint/ONNX/序列化
│   │   ├── s3_transport.py       # S3 trajectory IO
│   │   └── logger.py             # TensorBoard + Prometheus
│   ├── collector/                # Python 端 Collector
│   └── generated/                # Generated protobuf code
│
├── example/training/             # 端到端训练示例
├── Dockerfile.go                 # Go 仿真服务镜像 (<30MB)
├── Dockerfile.py                 # Python 训练镜像 (PyTorch+CUDA)
├── docker-compose.yml            # Redis + Go + Trainer 全栈
└── scripts/gen_proto.sh          # Proto 代码生成
```

## Quick Start

### 1. Setup Development Environment

```bash
make dev-setup
```

### 2. Generate Protobuf Code

```bash
make proto
```

### 3. Run Server

```bash
make run-server
```

### 4. Use Python Client

```python
from rl_env_engine.client import GrpcEnv

env = GrpcEnv(scenario="cartpole", host="127.0.0.1", port=9090)
obs, info = env.reset()

for _ in range(100):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        obs, info = env.reset()

env.close()
```

## Installation

### Go SDK

```bash
# Server SDK (for implementing new scenarios)
go get github.com/jelech/rl_env_engine/go/pkg/sdk@latest

# Client SDK (for connecting to servers)
go get github.com/jelech/rl_env_engine/go/pkg/client@latest
```

### Python SDK

#### 从 PyPI 安装（发布后）

```bash
# 基础安装（Client SDK）
pip install rl-env-engine

# 包含 Server SDK（FastAPI 服务端框架）
pip install rl-env-engine[server]

# 包含 RL 依赖（stable-baselines3, torch 等）
pip install rl-env-engine[rl]

# 完整安装
pip install rl-env-engine[all]
```

#### 本地开发安装

```bash
# 克隆仓库
git clone https://github.com/jelech/rl_env_engine.git
cd rl_env_engine

# 以可编辑模式安装 Python 包
pip install -e python/

# 或者包含所有依赖
pip install -e "python/[all]"
```

#### 从 GitHub 直接安装

```bash
# 安装最新版本
pip install git+https://github.com/jelech/rl_env_engine.git#subdirectory=python

# 安装特定分支
pip install git+https://github.com/jelech/rl_env_engine.git@main#subdirectory=python

# 安装特定 tag/版本
pip install git+https://github.com/jelech/rl_env_engine.git@v0.3.0#subdirectory=python

# 包含额外依赖
pip install "rl-env-engine[server] @ git+https://github.com/jelech/rl_env_engine.git#subdirectory=python"
```

## Available Make Commands

```bash
make help          # Show all available commands
make proto         # Generate Go and Python protobuf code
make build         # Build everything
make test          # Run all tests (Go + Python)
make run-server    # Run gRPC server
make clean         # Clean build artifacts
```

## Training Example

```bash
# 本地 CartPole 训练 (无需 Go server)
python example/training/run_cartpole_training.py

# DDP 多卡训练
torchrun --nproc_per_node=4 example/training/run_cartpole_training.py
```

## Docker

```bash
# 全栈启动 (Redis + Go仿真 + Python训练)
docker compose up --build

# 仅启动仿真服务
docker compose up redis simulation-server
```

## Built-in Scenarios

- **simple**: Mathematical test scenario for debugging
- **cartpole**: Classic CartPole control environment

## Python Server SDK (FastAPI)

除了 Go gRPC 服务器，还提供 Python FastAPI 服务器框架，适合快速构建仿真服务。

### 创建自定义场景服务

```python
from rl_env_engine.server import create_app, run_server, BaseScenario
from typing import Any, Dict

class MySimulation(BaseScenario):
    """自定义仿真场景"""
    
    @property
    def name(self) -> str:
        return "my_simulation"
    
    def create_environment(self, config: Dict[str, Any]) -> Any:
        # 创建并返回环境实例
        return {"state": 0, "config": config}
    
    def reset(self, env: Any, **kwargs) -> Dict[str, Any]:
        # 重置环境
        env["state"] = 0
        return {"observation": env["state"], "info": {}}
    
    def step(self, env: Any, action: Any, **kwargs) -> Dict[str, Any]:
        # 执行一步仿真
        env["state"] += action.get("value", 1)
        return {
            "observation": env["state"],
            "reward": 1.0,
            "terminated": env["state"] >= 100,
            "info": {},
        }
    
    def close(self, env: Any):
        # 清理资源
        pass

# 创建并运行服务
if __name__ == "__main__":
    app = create_app(
        scenarios=[MySimulation()],
        scenario_name="my_simulation",
        enable_discovery=True,  # 启用 Redis 服务发现
    )
    run_server(app, host="0.0.0.0", port=8000)
```

### 使用 SDK 调用服务

```python
from rl_env_engine.client import SimulationSDK

# 方式1: 通过服务发现
sdk = SimulationSDK(discovery_url="http://localhost:8000/ips")

# 方式2: 直接指定 Worker
sdk = SimulationSDK(direct_workers=["http://localhost:8000"])

# 创建会话
result = sdk.create_sessions(
    batch_size=2,
    scenario="my_simulation",
    config={"param": "value"},
)

# 批量执行 step
actions = [{"value": 1}, {"value": 2}]
results = sdk.batch_step(actions)

# 关闭所有会话
sdk.close()
```

## Creating Custom Scenarios (Go)

Implement the `core.Scenario` interface:

```go
import "github.com/jelech/rl_env_engine/go/pkg/core"

type MyScenario struct {
    name string
}

func (s *MyScenario) GetName() string { return s.name }
func (s *MyScenario) GetDescription() string { return "My custom scenario" }
func (s *MyScenario) CreateEnvironment(config core.Config) (core.Environment, error) {
    // Create and return your environment
}
func (s *MyScenario) ValidateConfig(config core.Config) error {
    // Validate configuration
}
```

## License

MIT
