# gRPC 强化学习环境客户端

通用的 gRPC 环境包装器，为仿真引擎提供标准化的强化学习环境接口。

> 📦 **本地安装（推荐）**
>
> 基础安装：
> ```bash
> pip install -e python_client
> ```
> 带强化学习依赖：
> ```bash
> pip install -e "python_client[rl]"
> ```
>
> 安装后导入：
> ```python
> from rl_env_engine_client import GrpcEnv, SimulationGrpcClient
> ```

这个包提供了通用的 gRPC 环境包装器，可连接任意仿真服务器，支持自动空间发现和多种动作类型。

## 功能特性

- **通用性**: 支持任意 gRPC 仿真服务和场景类型
- **自动空间发现**: 从服务器自动获取动作空间和观察空间定义
- **多种动作类型**: 支持数值、数组、布尔等多种动作数据类型
- **标准接口**: 兼容 Gymnasium 标准，可与主流强化学习库集成
- **灵活配置**: 支持自定义服务器地址、端口和场景配置

## 文件说明

- `grpc_env.py` - 通用gRPC环境包装器（⭐ 推荐）
- `grpc_client.py` - 基础gRPC客户端
- `simulation_pb2.py` / `simulation_pb2_grpc.py` - 由 proto 生成的 gRPC 代码（已随包分发）
- `simulation_pb2.pyi` - 类型存根文件（用于 IDE 自动补全和类型检查）
- `examples/` - 示例代码和测试脚本

## IDE 类型提示和自动补全

本包包含完整的类型存根文件（`.pyi`），支持 IDE 自动补全和类型检查：

### 支持的 IDE

- **VS Code** + Pylance（推荐）
- **PyCharm**（自动识别）
- **其他支持 Pyright 的编辑器**

### 使用示例

```python
from rl_env_engine_client import simulation_pb2

# 创建 Action 对象 - IDE 会提供自动补全
action = simulation_pb2.Action(float_value=1.5)
# 输入 action. 时，IDE 会显示所有可用属性：
# - float_value: float
# - int_value: int
# - bool_value: bool
# - float_array: FloatArray
# - int_array: IntArray
# - bool_array: BoolArray
# - string_value: str
# - raw_data: bytes

# 创建请求对象 - 有完整的类型提示
request = simulation_pb2.StepEnvironmentRequest(
    env_id="test_env",
    actions=[action]
)
# 输入 request. 时，IDE 会显示：
# - env_id: str
# - actions: RepeatedCompositeFieldContainer[Action]
```

### 生成类型存根

类型存根文件在生成 protobuf 代码时自动创建。如果需要重新生成：

```bash
# 在项目根目录运行
./gen_grpc.sh
```

这会自动生成 `simulation_pb2.pyi` 类型存根文件。

### 类型检查配置

项目已配置 `pyproject.toml` 支持类型检查。如果 IDE 没有显示类型提示：

1. 确保安装了 `mypy-protobuf`：`pip install mypy-protobuf`
2. 重启 IDE
3. 检查 IDE 的类型检查设置（VS Code: 确保 Pylance 已启用）

## 快速开始

### 1. 安装依赖

```bash
pip install -e python_client[rl]
```

### 2. 启动gRPC服务器

在项目根目录：
```bash
make dev-grpc      # 启动gRPC服务器（推荐）
```

### 3. 基本使用

```python
from rl_env_engine_client import GrpcEnv

# 创建环境连接
env = GrpcEnv(
    scenario="your_scenario",
    host="127.0.0.1", 
    port=9090,
    config={"max_steps": 100, "param1": "value1"}
)

# 标准 Gymnasium 接口
obs, info = env.reset()
action = env.action_space.sample()
obs, reward, terminated, truncated, info = env.step(action)

# 关闭环境
env.close()
```

### 4. 与强化学习库集成

```python
from rl_env_engine_client import GrpcEnv
from stable_baselines3 import PPO

# 创建环境
env = GrpcEnv(scenario="training_scenario", config={"max_steps": 200})

# 使用 Stable Baselines 3 训练
model = PPO("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=10000)

# 评估模型
obs, _ = env.reset()
for i in range(1000):
    action, _states = model.predict(obs)
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        obs, _ = env.reset()
```

## API 文档

### GrpcEnv 类

主要的通用 gRPC 环境包装器。

#### 初始化参数

- `scenario` (str): 服务器端的场景名称
- `host` (str, 可选): gRPC 服务器地址，默认 "127.0.0.1"
- `port` (int, 可选): gRPC 服务器端口，默认 9090
- `env_id` (str, 可选): 环境实例ID，默认自动生成
- `config` (Dict[str, Any], 可选): 传递给服务器的配置参数
- `auto_reset` (bool, 可选): 是否自动重置环境，默认 True

#### 主要方法

- `reset()`: 重置环境，返回初始观察和信息
- `step(action)`: 执行动作，返回新观察、奖励、终止状态、截断状态和信息
- `close()`: 关闭环境连接
- `get_available_scenarios()`: 获取服务器支持的场景列表

### 动作类型支持

环境支持多种动作类型的自动转换：

- **浮点数**: `1.5`
- **整数**: `42`
- **布尔值**: `True`/`False`
- **NumPy 数组**: `np.array([1.0, 2.0, 3.0])`
- **多维数组**: `np.array([[1, 2], [3, 4]])`

## 空间定义

环境自动从服务器获取动作空间和观察空间定义，支持：

- **Box**: 连续空间
- **Discrete**: 离散空间  
- **MultiDiscrete**: 多离散空间
- **MultiBinary**: 多二进制空间

## 配置示例

```python
# 基本配置
config = {
    "max_steps": 100,
    "learning_rate": 0.01,
    "difficulty": "medium"
}

# 高级配置
config = {
    "environment": {
        "physics": {
            "gravity": 9.8,
            "friction": 0.1
        },
        "rendering": {
            "width": 800,
            "height": 600
        }
    },
    "training": {
        "max_episodes": 1000,
        "early_stopping": True
    }
}

env = GrpcEnv(scenario="complex_sim", config=config)
```

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
