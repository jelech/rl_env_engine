# gRPC Simple Environment - SB3 Integration

这个目录包含了与gRPC简单环境集成的Python客户端代码，专门用于Stable Baselines 3 (SB3)强化学习训练。

## 文件说明

- `sb3_simple_env.py` - SB3兼容的gRPC环境包装器
- `sb3_training.py` - 使用SB3进行训练的完整示例
- `simple_grpc_test.py` - 基本的gRPC客户端测试
- `proto/` - 自动生成的protobuf Python文件

## 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt

# 或者单独安装主要依赖
pip install stable-baselines3[extra] gymnasium grpcio grpcio-tools
```

## 使用步骤

### 1. 启动gRPC服务器

在项目根目录：
```bash
# 构建并启动gRPC服务器
make build-grpc
./bin/grpc_server_example
```

服务器将在 `0.0.0.0:9090` 监听。

### 2. 测试环境连接

```bash
cd python_client
python sb3_simple_env.py
```

这将运行一个基本测试，验证环境是否正常工作。

### 3. 进行SB3训练

```bash
cd python_client
python sb3_training.py
```

选择不同的训练选项：
1. 训练PPO agent
2. 训练A2C agent
3. 比较算法性能
4. 超参数调优
5. 快速环境测试

## 环境详细说明

### Simple Environment

这是一个数学测试环境，用于：
- **目标**: 通过调整动作让 `current_value` 接近 `target_value`
- **观察空间**: `[current_value, target_value, step, max_steps, tolerance, reward]` (6维)
- **动作空间**: 连续值范围 `[-10, 10]` (1维)
- **奖励**: 距离目标越近奖励越高，到达目标获得最高奖励

### 配置参数

- `max_steps`: 最大步数 (默认: 50)
- `tolerance`: 容忍误差 (默认: 0.5)

## SB3环境特性

### 兼容性
- ✅ 完全兼容 Stable Baselines 3
- ✅ 支持 gymnasium 接口
- ✅ 通过 `check_env()` 验证
- ✅ 支持连续动作空间

### 算法支持
- **PPO** (Proximal Policy Optimization) - 推荐
- **A2C** (Advantage Actor-Critic)
- **SAC** (Soft Actor-Critic) - 适用于连续动作
- **TD3** (Twin Delayed Deep Deterministic) - 适用于连续动作

## 使用示例

### 基本使用

```python
from sb3_simple_env import SB3GrpcSimpleEnv
from stable_baselines3 import PPO

# 创建环境
env = SB3GrpcSimpleEnv(max_steps=50, tolerance=0.2)

# 创建和训练模型
model = PPO("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=50000)

# 保存模型
model.save("my_simple_model")

# 测试模型
obs, _ = env.reset()
for _ in range(100):
    action, _ = model.predict(obs, deterministic=True)
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        obs, _ = env.reset()

env.close()
```

### 自定义训练

```python
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from sb3_simple_env import SB3GrpcSimpleEnv

# 创建环境
env = SB3GrpcSimpleEnv(max_steps=30, tolerance=0.1)
env = Monitor(env)  # 监控训练过程

# 自定义PPO参数
model = PPO(
    "MlpPolicy",
    env,
    learning_rate=3e-4,
    n_steps=2048,
    batch_size=64,
    n_epochs=10,
    gamma=0.99,
    verbose=1,
    tensorboard_log="./tensorboard_logs/"
)

# 训练
model.learn(total_timesteps=100000)
model.save("custom_simple_model")

env.close()
```

## 性能指标

一个训练良好的agent应该能够：
- 在 10-20 步内收敛到目标
- 获得正向奖励
- 成功率 > 90%

## 故障排除

### 连接问题
```
ConnectionError: Failed to connect to gRPC server
```
**解决方案**: 确保gRPC服务器正在运行在正确的端口。

### 环境检查失败
```
AssertionError during check_env()
```
**解决方案**: 检查观察和动作空间定义，确保返回值格式正确。

### 训练不收敛
- 尝试调整学习率 (1e-4 到 1e-3)
- 增加训练步数
- 调整网络结构
- 检查奖励函数设计

## 扩展

你可以基于这个基础环境：
1. 添加更复杂的观察空间
2. 实现多智能体环境
3. 添加连续动作空间的约束
4. 集成其他RL算法

## 监控和可视化

使用 TensorBoard 监控训练：
```bash
tensorboard --logdir ./ppo_simple_tensorboard/
```

在浏览器中打开 `http://localhost:6006` 查看训练曲线。
