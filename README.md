# RL Env Engine

一个面向强化学习（RL）的高性能仿真框架，支持多场景、多环境并发训练，提供 gRPC 与 HTTP 两套 API，并内置 Python 环境包装器。

## 特性总览
- 多场景支持：可扩展的场景架构，便于算法验证与原型开发
- 双 API：gRPC（高性能）与 HTTP（调试友好）
- Python 生态：通用环境包装器，开箱即用
- 插件式扩展：实现并注册 Scenario 即可新增场景
- 监控友好：内置性能监控与详细日志开关
- 生产可用：支持多环境并发、资源自动回收、批量操作

## 前置条件
- Go 1.20+（推荐 1.21+）
- Python 3.9+（强化学习库推荐 3.8–3.11 区间）
- protoc 与 protoc-gen-go（用于生成 gRPC 代码）
- Make 与基本构建工具链

## 安装

### Go 模块安装
```bash
# 在你的Go项目中引入rl_env_engine
go get github.com/jelech/rl_env_engine

# 或者克隆仓库进行开发
git clone https://github.com/jelech/rl_env_engine.git
cd rl_env_engine
go mod tidy
```

### Python 客户端安装

#### 方式一：本地开发安装（推荐）
```bash
git clone https://github.com/jelech/rl_env_engine.git
cd rl_env_engine/python_client

# 基础安装
pip install -e .

# 安装强化学习相关依赖
pip install -e ".[rl]"
```

#### 方式二：直接从 GitHub 安装
```bash
# 基础安装
pip install "git+https://github.com/jelech/rl_env_engine.git#subdirectory=python_client"

# 安装强化学习相关依赖
pip install "git+https://github.com/jelech/rl_env_engine.git#subdirectory=python_client&egg=rl-env-engine-client[rl]"
```

#### 验证安装
```bash
# 验证Go安装
go run examples/dual_server/main.go

# 验证Python安装
python -c "from rl_env_engine_client import GrpcEnv; print('安装成功！')"
```

## 快速开始

> 💡 **提示**：请先完成上述[安装](#安装)步骤

### 1) 启动 gRPC 服务器（推荐）
```bash
make dev-grpc
# 默认监听: 127.0.0.1:9090
```

### 2) 使用 Python 环境包装器
```bash
# 如果已完成本地安装
python -c "from rl_env_engine_client import GrpcEnv; print('Ready to use!')"

# 或者运行完整示例
cd python_client
python -m rl_env_engine_client.grpc_env
```

### 3) 启动 HTTP 服务器（可选，便于调试）
```bash
make run-server
# 默认监听: 127.0.0.1:8080
```

## API 概览

### gRPC
- GetInfo() — 获取服务信息
- GetSpaces() — 获取动作空间和观察空间定义
- CreateEnvironment() — 创建环境
- ResetEnvironment() — 重置环境
- StepEnvironment() — 执行一步
- CloseEnvironment() — 关闭环境

默认地址：127.0.0.1:9090

### HTTP
- GET /info — 获取服务信息
- POST /env — 创建环境
- POST /env/{id}/reset — 重置环境
- POST /env/{id}/step — 执行一步
- DELETE /env/{id} — 删除环境

默认地址：http://127.0.0.1:8080

## Python 集成

### 通用环境包装器（推荐）
```python
from rl_env_engine_client import GrpcEnv
from stable_baselines3 import PPO

# 连接 gRPC 服务
env = GrpcEnv(scenario="training_scenario", config={"max_steps": 50, "tolerance": 0.2})

model = PPO("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=50000)

model.save("my_model")
env.close()
```

### 基础 gRPC 客户端示例
```python
import grpc
from rl_env_engine_client import simulation_pb2, simulation_pb2_grpc

channel = grpc.insecure_channel("127.0.0.1:9090")
client = simulation_pb2_grpc.SimulationServiceStub(channel)

resp = client.CreateEnvironment(
    simulation_pb2.CreateEnvironmentRequest(
        env_id="test_env",
        scenario="default",
        config={"max_steps": "50", "tolerance": "0.5"},
    )
)
print(resp)
```

## Go 使用示例

### 启动 gRPC API 服务
```go
package main

import (
    simulations "github.com/jelech/rl_env_engine"
)

func main() {
    cfg := simulations.NewGrpcServerConfig(9090)
    simulations.StartGrpcServer(cfg)
}
```

### 同时启动 HTTP + gRPC
```go
package main

import (
    simulations "github.com/jelech/rl_env_engine"
)

func main() {
    cfg := &simulations.ServerConfig{
        HTTPConfig: simulations.NewHTTPServerConfig(8080),
        GrpcConfig: simulations.NewGrpcServerConfig(9090),
    }
    simulations.StartServersAndWait(cfg)
}
```

### 运行一次完整仿真（伪代码示例）
```go
package main

import (
    "context"
    "fmt"
    simulations "github.com/jelech/rl_env_engine"
)

func main() {
    config := map[string]interface{}{
        "env_name":   "demo",
        "sim_length": 30,
    }

    actionFunc := func(obs []simulations.Observation) []simulations.Action {
        return []simulations.Action{
            simulations.NewAction(map[string]float32{"a": 1.0, "b": 0.9}),
        }
    }

    if err := simulations.RunSimulation("default", config, 10, actionFunc); err != nil {
        panic(err)
    }
}
```

## 项目结构
```
.
├── core/                   # 核心仿真引擎
├── scenarios/              # 仿真场景实现
├── server/                 # 服务器实现
│   ├── grpc_server.go      # gRPC 服务
│   └── gym_api.go          # HTTP API
├── proto/                  # protobuf 定义
├── examples/               # 示例程序
├── python_client/          # Python 客户端
│   ├── rl_env_engine_client/   # 客户端包
│   │   ├── grpc_env.py     # 通用环境包装器
│   │   └── grpc_client.py  # gRPC 客户端
│   └── examples/           # 示例代码
└── Makefile                # 构建脚本
```

## 构建与开发

### 常用命令
```bash
# 构建所有组件
make build

# 仅构建 gRPC 服务器
make build-grpc

# 仅构建 HTTP 服务器
make build-server

# 初始化开发环境（安装工具链/依赖）
make dev-setup

# 生成 Python protobuf
make proto-python

# 运行测试
make test

# Python 端到端测试（HTTP）
make test-python

# 代码格式与静态检查
make fmt && make vet
```

## 扩展场景

### 1) 实现新场景
```go
type MyScenario struct{}

func (s *MyScenario) GetName() string { return "my_scenario" }

func (s *MyScenario) CreateEnvironment(config core.Config) (core.Environment, error) {
    // 创建环境逻辑
    // return env, nil
}

func (s *MyScenario) ValidateConfig(config core.Config) error {
    // 配置校验
    return nil
}
```

### 2) 注册场景
```go
func registerBuiltinScenarios(engine *core.SimulationEngine) {
    engine.RegisterScenario(&MyScenario{})
}
```

## 性能与监控

- gRPC 比 HTTP 通常快 30–50%
- 支持多环境并发训练，注意 CPU/内存配比
- 支持批量环境操作与资源自动回收
- 内置监控指标：QPS、延迟、P50/P95/P99 等
- 日志监控
  ```bash
  tail -f grpc_server.log
  DEBUG=1 make dev-grpc
  ```

## 示例与演示

- 运行示例
  ```bash
  go run examples/dual_server/main.go
  ```
- 启动 HTTP 服务示例
  ```bash
  go run examples/server/main.go --port 8080
  ```
- 测试 Python 客户端（需先启动服务）
  ```bash
  cd python_client
  python -m rl_env_engine_client.grpc_env
  ```

## 贡献
1) Fork 项目
2) 创建特性分支：git checkout -b feature/new-scenario
3) 提交更改：git commit -m "feat: add new scenario"
4) 推送分支：git push origin feature/new-scenario
5) 提交 Pull Request

## 许可证
MIT，详见 LICENSE。

## 联系方式
如有问题或建议，请提交 Issue 或联系维护团队。
