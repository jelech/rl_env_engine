#!/usr/bin/env python3
"""
SB3 (Stable Baselines 3) 兼容的gRPC环境包装器
用于与简单数学测试场景进行强化学习训练
"""

import grpc
import numpy as np
import gymnasium as gym  # 新版本使用gymnasium
from gymnasium import spaces
from proto import simulation_pb2, simulation_pb2_grpc


class SB3GrpcSimpleEnv(gym.Env):
    """
    SB3兼容的gRPC简单环境

    环境描述：
    - 目标：通过调整action让current_value接近target_value
    - 观察空间：[current_value, target_value, step, max_steps, tolerance, reward]
    - 动作空间：连续值 [-10, 10]
    - 奖励：距离target_value越近奖励越高
    """

    metadata = {"render.modes": ["human"]}

    def __init__(self, host="127.0.0.1", port=9090, env_id=None, max_steps=50, tolerance=0.5):
        super(SB3GrpcSimpleEnv, self).__init__()

        self.host = host
        self.port = port
        self.env_id = env_id or f"sb3_env_{np.random.randint(1000, 9999)}"
        self.max_steps = max_steps
        self.tolerance = tolerance

        self.channel = None
        self.client = None
        self._env_created = False

        # 定义动作和观察空间
        # 动作空间：连续值范围 [-10, 10]
        self.action_space = spaces.Box(low=-10.0, high=10.0, shape=(1,), dtype=np.float32)

        # 观察空间：[current_value, target_value, step, max_steps, tolerance, reward]
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(6,), dtype=np.float32)

        # 连接到服务器
        self._connect()

    def _connect(self):
        """连接到gRPC服务器"""
        try:
            self.channel = grpc.insecure_channel(f"{self.host}:{self.port}")
            self.client = simulation_pb2_grpc.SimulationServiceStub(self.channel)

            # 测试连接
            info_request = simulation_pb2.GetInfoRequest()
            response = self.client.GetInfo(info_request)
            print(f"Connected to: {response.name} v{response.version}")

        except Exception as e:
            raise ConnectionError(f"Failed to connect to gRPC server: {e}")

    def _create_environment(self):
        """创建环境（如果尚未创建）"""
        if self._env_created:
            return

        config = {"max_steps": str(self.max_steps), "tolerance": str(self.tolerance)}

        request = simulation_pb2.CreateEnvironmentRequest(env_id=self.env_id, scenario="simple", config=config)

        response = self.client.CreateEnvironment(request)
        if not response.success:
            raise RuntimeError(f"Failed to create environment: {response.message}")

        self._env_created = True
        print(f"Environment created: {self.env_id}")

    def reset(self, seed=None, options=None):
        """重置环境"""
        super().reset(seed=seed)

        # 确保环境已创建
        self._create_environment()

        request = simulation_pb2.ResetEnvironmentRequest(env_id=self.env_id)
        response = self.client.ResetEnvironment(request)

        # 解析观察数据
        obs_data = response.observations[0].data
        observation = np.array([float(x) for x in obs_data], dtype=np.float32)

        # gymnasium格式要求返回 (observation, info)
        info = {
            "current_value": observation[0],
            "target_value": observation[1],
            "step": int(observation[2]),
            "max_steps": int(observation[3]),
            "tolerance": observation[4],
        }

        return observation, info

    def step(self, action):
        """执行一步"""
        # 确保action是正确格式
        if isinstance(action, np.ndarray):
            action_value = float(action[0])
        else:
            action_value = float(action)

        # 创建gRPC action
        simple_action = simulation_pb2.SimpleAction(value=action_value)
        grpc_action = simulation_pb2.Action(simple_action=simple_action)

        request = simulation_pb2.StepEnvironmentRequest(env_id=self.env_id, action=grpc_action)

        response = self.client.StepEnvironment(request)

        # 解析响应
        obs_data = response.observations[0].data
        observation = np.array([float(x) for x in obs_data], dtype=np.float32)
        reward = float(response.rewards[0])
        terminated = bool(response.done[0])
        truncated = False  # 在我们的环境中，terminated即为完成

        info = {
            "current_value": observation[0],
            "target_value": observation[1],
            "step": int(observation[2]),
            "max_steps": int(observation[3]),
            "tolerance": observation[4],
            "action_taken": action_value,
        }

        return observation, reward, terminated, truncated, info

    def close(self):
        """关闭环境"""
        if self.client and self._env_created:
            try:
                request = simulation_pb2.CloseEnvironmentRequest(env_id=self.env_id)
                response = self.client.CloseEnvironment(request)
                print(f"Environment closed: {response.message}")
            except Exception as e:
                print(f"Error closing environment: {e}")
            finally:
                self._env_created = False

        if self.channel:
            self.channel.close()

    def render(self, mode="human"):
        """渲染（目前为空实现）"""
        pass


def test_sb3_env():
    """测试SB3兼容环境"""
    print("Testing SB3-compatible gRPC Simple Environment...")

    # 创建环境
    env = SB3GrpcSimpleEnv(max_steps=20, tolerance=0.3)

    try:
        # 重置环境
        obs, info = env.reset()
        print(f"Initial observation: {obs}")
        print(f"Initial info: {info}")

        total_reward = 0
        step_count = 0

        # 运行一个episode
        while True:
            # 简单策略：朝目标方向移动
            current_value = obs[0]
            target_value = obs[1]

            # 计算朝目标移动的动作 (带一些随机性)
            diff = target_value - current_value
            action = np.array([diff * 0.7 + np.random.normal(0, 0.1)])
            action = np.clip(action, -10, 10)  # 限制动作范围

            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            step_count += 1

            print(
                f"Step {step_count}: action={action[0]:.3f}, "
                f"current={obs[0]:.3f}, reward={reward:.3f}, "
                f"done={terminated}"
            )

            if terminated or truncated:
                print(f"Episode finished! Total reward: {total_reward:.3f}")
                break

        print("Test completed successfully!")

        # 测试多个episodes
        print("\nTesting multiple episodes...")
        for episode in range(3):
            obs, _ = env.reset()
            episode_reward = 0
            steps = 0

            while True:
                current_value = obs[0]
                target_value = obs[1]
                diff = target_value - current_value
                action = np.array([diff * 0.8])

                obs, reward, terminated, truncated, info = env.step(action)
                episode_reward += reward
                steps += 1

                if terminated or truncated:
                    break

            print(f"Episode {episode + 1}: {steps} steps, " f"reward: {episode_reward:.3f}")

    finally:
        env.close()


if __name__ == "__main__":
    test_sb3_env()
