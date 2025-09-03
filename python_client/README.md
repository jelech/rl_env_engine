# Python Client for Simulation Framework

这个目录包含了Python客户端，用于与Go仿真服务器进行交互，支持HTTP和gRPC两种方式，并提供了Stable Baselines 3 (SB3)集成。

## 文件说明

- `sb3_simple_env.py` - SB3兼容的gRPC环境包装器（⭐ 推荐）
- `sb3_training.py` - 完整的SB3训练示例
- `grpc_client.py` - 基础gRPC客户端
- `simulation_gym.py` - HTTP API的Gym接口（兼容）
- `rl_training.py` - HTTP版强化学习训练示例
- `test_api.py` - HTTP API测试脚本
- `proto/` - 自动生成的protobuf Python文件
- `requirements.txt` - Python依赖列表

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动Go服务器

在项目根目录：
```bash
# 启动gRPC服务器（推荐）
make dev-grpc

# 或启动HTTP服务器（兼容）
make run-server
```

### 3. SB3强化学习训练

```bash
# 使用gRPC环境进行SB3训练
python sb3_training.py
```

## SB3环境使用

### 基本使用

```python
from sb3_simple_env import SB3GrpcSimpleEnv
from stable_baselines3 import PPO

# 创建环境
env = SB3GrpcSimpleEnv(max_steps=50, tolerance=0.2)

# 训练模型
model = PPO("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=50000)

# 保存和测试
model.save("my_model")
env.close()
```

### 训练配置

```python
# 自定义环境参数
env = SB3GrpcSimpleEnv(
    host='127.0.0.1',           # 服务器地址
    port=9090,                  # 服务器端口
    max_steps=100,              # 最大步数
    tolerance=0.1               # 容忍误差
)

# 自定义PPO参数
model = PPO(
    "MlpPolicy", 
    env,
    learning_rate=3e-4,
    n_steps=2048,
    batch_size=64,
    verbose=1,
    tensorboard_log="./logs/"
)
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

## 兼容的算法

- ✅ **PPO** (Proximal Policy Optimization) - 推荐
- ✅ **A2C** (Advantage Actor-Critic) - 快速训练
- ✅ **SAC** (Soft Actor-Critic) - 连续动作专家
- ✅ **TD3** (Twin Delayed Deep Deterministic) - 高级算法

## 监控训练

### TensorBoard
```bash
# 启动TensorBoard
tensorboard --logdir ./logs/

# 打开浏览器访问 http://localhost:6006
```

### 关键指标
- `rollout/ep_rew_mean`: 平均episode奖励
- `rollout/ep_len_mean`: 平均episode长度  
- `train/learning_rate`: 学习率变化
- `train/value_loss`: 价值函数损失

## 故障排除

### gRPC连接失败
```bash
# 检查服务器是否运行
lsof -i :9090

# 重启gRPC服务器
make dev-grpc
```

### 训练不收敛
```python
# 尝试调整学习率
model = PPO("MlpPolicy", env, learning_rate=1e-4)

# 增加训练步数
model.learn(total_timesteps=100000)

# 调整网络结构
model = PPO("MlpPolicy", env, policy_kwargs=dict(net_arch=[64, 64]))
```

### 环境检查失败
```python
# 验证环境
from stable_baselines3.common.env_checker import check_env
check_env(env)
```

## 性能对比

| 接口类型 | 延迟 | 吞吐量 | 使用场景           |
| -------- | ---- | ------ | ------------------ |
| gRPC     | 低   | 高     | 高频训练、实时仿真 |
| HTTP     | 中   | 中     | 调试、兼容性       |

## 示例

### 完整训练流程
```python
from sb3_simple_env import SB3GrpcSimpleEnv
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor

# 创建和包装环境
env = SB3GrpcSimpleEnv(max_steps=30, tolerance=0.2)
env = Monitor(env)

# 训练
model = PPO("MlpPolicy", env, verbose=1, tensorboard_log="./logs/")
model.learn(total_timesteps=50000)

# 测试
obs, _ = env.reset()
for _ in range(100):
    action, _ = model.predict(obs, deterministic=True)
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        obs, _ = env.reset()

env.close()
```
