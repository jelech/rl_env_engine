#!/usr/bin/env python3
"""
Simple gRPC client to test the simple scenario with SB3 compatibility
"""

import grpc
import numpy as np
from proto import simulation_pb2, simulation_pb2_grpc
import gym
from gym import spaces


class SimpleGrpcEnv(gym.Env):
    """OpenAI Gym环境包装器，用于gRPC简单场景"""

    def __init__(self, host="127.0.0.1", port=9090, env_id="python_simple_env"):
        super(SimpleGrpcEnv, self).__init__()

        self.host = host
        self.port = port
        self.env_id = env_id
        self.channel = None
        self.client = None

        # 定义动作和观察空间
        # 动作空间：连续值范围 [-10, 10]
        self.action_space = spaces.Box(low=-10.0, high=10.0, shape=(1,), dtype=np.float32)

        # 观察空间：[current_value, target_value, step, max_steps, tolerance, reward]
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(6,), dtype=np.float32)

        self._connect()
        self._create_environment()

    def _connect(self):
        """连接到gRPC服务器"""
        self.channel = grpc.insecure_channel(f"{self.host}:{self.port}")
        self.client = simulation_pb2_grpc.SimulationServiceStub(self.channel)
        print(f"Connected to gRPC server at {self.host}:{self.port}")

    def _create_environment(self):
        """创建环境"""
        config = {"max_steps": "50", "tolerance": "0.5"}

        request = simulation_pb2.CreateEnvironmentRequest(env_id=self.env_id, scenario="simple", config=config)

        response = self.client.CreateEnvironment(request)
        if not response.success:
            raise RuntimeError(f"Failed to create environment: {response.message}")

        print(f"Environment created: {response.message}")

    def reset(self):
        """重置环境"""
        request = simulation_pb2.ResetEnvironmentRequest(env_id=self.env_id)
        response = self.client.ResetEnvironment(request)

        # 解析观察数据
        obs_data = response.observations[0].data
        observation = np.array([float(x) for x in obs_data], dtype=np.float32)

        return observation

    def step(self, action):
        """执行一步"""
        # 确保action是float
        action_value = float(action[0]) if hasattr(action, "__len__") else float(action)

        # 创建SimpleAction
        simple_action = simulation_pb2.SimpleAction(value=action_value)
        grpc_action = simulation_pb2.Action(simple_action=simple_action)

        request = simulation_pb2.StepEnvironmentRequest(env_id=self.env_id, action=grpc_action)

        response = self.client.StepEnvironment(request)

        # 解析响应
        obs_data = response.observations[0].data
        observation = np.array([float(x) for x in obs_data], dtype=np.float32)
        reward = response.rewards[0]
        done = response.done[0]
        info = {"step": int(obs_data[2])}  # 步数信息

        return observation, reward, done, info

    def close(self):
        """关闭环境"""
        if self.client:
            request = simulation_pb2.CloseEnvironmentRequest(env_id=self.env_id)
            response = self.client.CloseEnvironment(request)
            print(f"Environment closed: {response.message}")

        if self.channel:
            self.channel.close()

    def render(self, mode="human"):
        """渲染（简单打印）"""
        pass


def test_simple_env():
    """测试简单环境"""
    env = SimpleGrpcEnv()

    try:
        print("Testing Simple gRPC Environment...")

        # 重置环境
        obs = env.reset()
        print(f"Initial observation: {obs}")
        print(f"  Current value: {obs[0]:.3f}")
        print(f"  Target value: {obs[1]:.3f}")
        print(f"  Step: {obs[2]}")
        print(f"  Max steps: {obs[3]}")
        print(f"  Tolerance: {obs[4]}")
        print(f"  Reward: {obs[5]:.3f}")

        # 运行几步
        for step in range(5):
            # 简单策略：朝目标方向移动
            current_value = obs[0]
            target_value = obs[1]

            # 计算朝目标移动的动作
            diff = target_value - current_value
            action = np.array([diff * 0.8])  # 80% 的差值

            obs, reward, done, info = env.step(action)

            print(f"\nStep {step + 1}:")
            print(f"  Action: {action[0]:.3f}")
            print(f"  New observation: {obs}")
            print(f"  Current value: {obs[0]:.3f}")
            print(f"  Reward: {reward:.3f}")
            print(f"  Done: {done}")
            print(f"  Info: {info}")

            if done:
                print("Environment completed!")
                break

        print("\nTest completed successfully!")

    finally:
        env.close()


if __name__ == "__main__":
    test_simple_env()
