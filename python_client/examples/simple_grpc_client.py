#!/usr/bin/env python3
"""
Python客户端测试简单场景（用于SB3集成）
"""
import grpc
import numpy as np
import time
import sys
import os

# 添加proto生成的代码到路径
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "proto"))

try:
    import simulation_pb2
    import simulation_pb2_grpc
except ImportError as e:
    print(f"Error importing protobuf modules: {e}")
    print("Please generate Python protobuf files first:")
    print(
        "cd .. && python -m grpc_tools.protoc --python_out=python_client --grpc_python_out=python_client -I proto proto/simulation.proto"
    )
    sys.exit(1)


class SimpleGymEnv:
    """
    简单仿真环境的Python包装器，兼容OpenAI Gym接口
    可以用于与Stable Baselines 3 (SB3) 集成
    """

    def __init__(self, server_address="localhost:9090", max_steps=100, tolerance=0.5):
        self.server_address = server_address
        self.max_steps = max_steps
        self.tolerance = tolerance
        self.channel = None
        self.stub = None
        self.env_id = "simple_env_python"
        self._current_step = 0

    def connect(self):
        """连接到gRPC服务器"""
        try:
            self.channel = grpc.insecure_channel(self.server_address)
            self.stub = simulation_pb2_grpc.SimulationServiceStub(self.channel)
            print(f"Connected to gRPC server at {self.server_address}")

            # 创建环境
            request = simulation_pb2.CreateEnvironmentRequest(
                env_id=self.env_id,
                scenario="simple",
                config={"max_steps": str(self.max_steps), "tolerance": str(self.tolerance)},
            )
            response = self.stub.CreateEnvironment(request)
            if not response.success:
                raise Exception(f"Failed to create environment: {response.message}")

            print(f"Environment created: {response.message}")
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.stub:
            try:
                request = simulation_pb2.CloseEnvironmentRequest(env_id=self.env_id)
                response = self.stub.CloseEnvironment(request)
                print(f"Environment closed: {response.message}")
            except Exception as e:
                print(f"Error closing environment: {e}")

        if self.channel:
            self.channel.close()
            print("Disconnected from gRPC server")

    def reset(self):
        """重置环境，返回初始观察"""
        try:
            request = simulation_pb2.ResetEnvironmentRequest(env_id=self.env_id)
            response = self.stub.ResetEnvironment(request)

            if len(response.observations) == 0:
                raise Exception("No observations returned from reset")

            observation = np.array(response.observations[0].data, dtype=np.float32)
            self._current_step = 0

            print(f"Environment reset. Initial observation shape: {observation.shape}")
            print(f"Observation: {observation}")

            return observation
        except Exception as e:
            print(f"Reset failed: {e}")
            raise

    def step(self, action):
        """
        执行一步

        Args:
            action: float, 要执行的动作值

        Returns:
            observation: np.array, 新的观察
            reward: float, 奖励
            done: bool, 是否完成
            info: dict, 额外信息
        """
        try:
            # 创建SimpleAction
            simple_action = simulation_pb2.SimpleAction(value=float(action))
            action_proto = simulation_pb2.Action(simple_action=simple_action)

            request = simulation_pb2.StepEnvironmentRequest(env_id=self.env_id, action=action_proto)
            response = self.stub.StepEnvironment(request)

            if len(response.observations) == 0:
                raise Exception("No observations returned from step")

            observation = np.array(response.observations[0].data, dtype=np.float32)
            reward = response.rewards[0] if response.rewards else 0.0
            done = response.done[0] if response.done else False
            info = dict(response.info)

            self._current_step += 1

            return observation, reward, done, info
        except Exception as e:
            print(f"Step failed: {e}")
            raise

    @property
    def observation_space_shape(self):
        """观察空间的形状"""
        return (6,)  # 简单环境有6个观察值

    @property
    def action_space_range(self):
        """动作空间的范围"""
        return (-5.0, 5.0)  # 动作值范围


def test_simple_environment():
    """测试简单环境"""
    print("Testing Simple Environment")
    print("=" * 50)

    env = SimpleGymEnv(max_steps=20, tolerance=0.5)

    if not env.connect():
        return

    try:
        # 运行几个episode
        for episode in range(3):
            print(f"\n--- Episode {episode + 1} ---")

            # 重置环境
            obs = env.reset()
            current_value = obs[0]
            target_value = obs[1]
            difference = obs[2]

            print(f"Initial: current={current_value:.2f}, target={target_value:.2f}, diff={difference:.2f}")

            episode_reward = 0
            for step in range(20):
                # 简单策略：朝目标方向移动
                if abs(difference) < 0.1:
                    action = 0.0  # 已经接近目标，停止
                elif difference > 0:
                    action = min(1.0, difference * 0.8)  # 正向移动
                else:
                    action = max(-1.0, difference * 0.8)  # 负向移动

                # 执行步骤
                obs, reward, done, info = env.step(action)
                episode_reward += reward

                current_value = obs[0]
                target_value = obs[1]
                difference = obs[2]

                print(
                    f"Step {step + 1}: action={action:.2f}, current={current_value:.2f}, "
                    f"target={target_value:.2f}, diff={difference:.2f}, reward={reward:.2f}, done={done}"
                )

                if done:
                    print(f"Episode completed after {step + 1} steps!")
                    break

            print(f"Episode {episode + 1} total reward: {episode_reward:.2f}")

    finally:
        env.disconnect()

    print("\nTest completed!")


def demo_for_sb3():
    """演示如何与SB3集成的接口"""
    print("\nDemo for SB3 Integration")
    print("=" * 50)

    # 这里展示如何创建兼容SB3的环境包装器
    print("To integrate with Stable Baselines 3, you can wrap this environment:")
    print(
        """
import gymnasium as gym
from gymnasium import spaces

class SimpleEnvWrapper(gym.Env):
    def __init__(self):
        super().__init__()
        self.env = SimpleGymEnv()
        self.env.connect()
        
        # 定义观察和动作空间
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, 
            shape=self.env.observation_space_shape, 
            dtype=np.float32
        )
        self.action_space = spaces.Box(
            low=self.env.action_space_range[0], 
            high=self.env.action_space_range[1], 
            shape=(1,), 
            dtype=np.float32
        )
    
    def reset(self, seed=None, options=None):
        obs = self.env.reset()
        return obs, {}
    
    def step(self, action):
        return self.env.step(action[0])
    
    def close(self):
        self.env.disconnect()

# 使用示例：
# env = SimpleEnvWrapper()
# model = PPO("MlpPolicy", env, verbose=1)
# model.learn(total_timesteps=10000)
"""
    )


if __name__ == "__main__":
    print("Simple Environment gRPC Client Test")
    print("确保gRPC服务器正在运行在localhost:9090")
    print("-" * 50)

    test_simple_environment()
    demo_for_sb3()
