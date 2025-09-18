# Python Client for Simulation Framework

> 可通过 pip 直接从 GitHub 安装：
>
> 基础安装：
> ```bash
> pip install "git+https://github.com/jelech/rl_env_engine.git#subdirectory=python_client"
> ```
> 带强化学习依赖 (extras: rl)：
> ```bash
> pip install "git+https://github.com/jelech/rl_env_engine.git#subdirectory=python_client&egg=rl-env-engine-client[rl]"
> ```
>
> 安装后导入：
> ```python
> from rl_env_engine_client import SB3GrpcSimpleEnv, SimulationGrpcClient
> ```

这个目录包含了Python客户端，用于与Go仿真服务器进行交互，支持HTTP和gRPC两种方式，并提供了Stable Baselines 3 (SB3)集成。

## 文件说明

- `sb3_simple_env.py` - SB3兼容的gRPC环境包装器（⭐ 推荐）
- `sb3_training.py` - 完整的SB3训练示例
- `grpc_client.py` - 基础gRPC客户端
- `simulation_gym.py` - HTTP API的Gym接口（兼容）
- `rl_training.py` - HTTP版强化学习训练示例
- `simulation_pb2.py` / `simulation_pb2_grpc.py` - 由 proto 生成的 gRPC 代码（已随包分发）
- `requirements.txt` - 旧版依赖列表（现在使用 `pyproject.toml`）

## 快速开始

### 1. 安装依赖（若源码方式）

```bash
pip install -e ./python_client[rl]
```

或使用 Git 安装（推荐）：
```bash
pip install "git+https://github.com/jelech/rl_env_engine.git#subdirectory=python_client"
```

### 2. 启动Go服务器

在项目根目录：
```bash
make dev-grpc      # 启动gRPC服务器（推荐）
# 或
make run-server    # 启动HTTP服务器
```

### 3. SB3强化学习训练

```bash
python -m rl_env_engine_client.sb3_training
```

或直接引用：
```python
from rl_env_engine_client import SB3GrpcSimpleEnv
from stable_baselines3 import PPO

env = SB3GrpcSimpleEnv(max_steps=50, tolerance=0.2)
model = PPO("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=10_000)
```

## 环境说明

### Simple Environment
- **目标**: 让 `current_value` 接近 `target_value`
- **观察空间**: `[current_value, target_value, step, max_steps, tolerance, reward]` (6维)
- **动作空间**: 连续值 `[-10, 10]` (1维)
- **奖励函数**: 距离越近奖励越高，到达目标获得额外奖励

### 配置参数
- `max_steps`: 最大步数（默认50）
- `tolerance`: 容忍误差（默认0.5）

## 安装问题排查

| 问题                                  | 可能原因                      | 解决                                |
| ------------------------------------- | ----------------------------- | ----------------------------------- |
| `ModuleNotFoundError: simulation_pb2` | gRPC 代码未生成或包未正确安装 | 使用 pip Git 安装或确保文件存在     |
| `grpcio` 编译失败                     | Python 版本或系统不兼容       | 升级 pip / 更换 Python 版本 (>=3.8) |
| 训练卡住                              | 服务器未启动                  | 先运行 `make dev-grpc`              |

## 旧有本地开发方式迁移说明

之前通过：
```python
sys.path.append('proto')
```
现在不需要；所有 protobuf 代码已包含在发布包中。

## 后续计划建议
- 发布到 PyPI (`rl-env-engine-client`)
- 增加多场景支持自动发现
- 增加异步客户端 (asyncio)
- 增加批量 step 接口以减少 RPC 次数

---
如需调试：
```bash
pip uninstall rl-env-engine-client -y
pip install -e ./python_client
```
