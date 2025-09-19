#!/usr/bin/env python3
"""
通用gRPC强化学习环境包装器
提供与gRPC服务器的标准化强化学习环境接口
"""

import grpc
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import Dict, Any, Optional, Union, Tuple

# 优先尝试包内相对导入（安装后）
try:
    from . import simulation_pb2, simulation_pb2_grpc  # type: ignore
except Exception:  # pragma: no cover
    # 回退：兼容直接在源码目录运行（未通过pip安装时）
    try:
        import simulation_pb2  # type: ignore
        import simulation_pb2_grpc  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "Cannot import simulation_pb2. Generate it via protoc or ensure package is installed."  # noqa: E501
        ) from e


class GrpcEnv(gym.Env):
    """
    通用gRPC环境包装器

    提供标准化的强化学习环境接口，连接远程gRPC仿真服务。
    支持：
    - 自动获取动作空间和观察空间定义
    - 多种动作类型（数值、数组、布尔等）
    - 任意场景类型和配置
    - 灵活的参数配置
    """

    metadata = {"render.modes": ["human"]}

    def __init__(
        self,
        scenario: str,
        host: str = "127.0.0.1",
        port: int = 9090,
        env_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        auto_reset: bool = True,
    ):
        """
        初始化gRPC环境连接

        Args:
            scenario: 服务器端的场景名称
            host: gRPC服务器地址
            port: gRPC服务器端口
            env_id: 环境实例ID（如果为None则自动生成）
            config: 传递给服务器的配置参数
            auto_reset: 是否自动重置环境
        """
        super(GrpcEnv, self).__init__()

        self.scenario = scenario
        self.host = host
        self.port = port
        self.env_id = env_id or f"grpc_env_{scenario}_{np.random.randint(1000, 9999)}"
        self.config = config or {}
        self.auto_reset = auto_reset

        self.channel = None
        self.client = None
        self._env_created = False
        self._spaces_loaded = False

        # 连接到服务器
        self._connect()

        # 获取空间定义
        self._setup_spaces()

    def _connect(self):
        """连接到gRPC服务器"""
        try:
            self.channel = grpc.insecure_channel(f"{self.host}:{self.port}")
            self.client = simulation_pb2_grpc.SimulationServiceStub(self.channel)

            # 测试连接
            info_request = simulation_pb2.GetInfoRequest()
            response = self.client.GetInfo(info_request)
            print(f"Connected to: {response.name} v{response.version}")
            print(f"Available scenarios: {list(response.scenarios)}")

        except Exception as e:
            raise ConnectionError(f"Failed to connect to gRPC server at {self.host}:{self.port}: {e}")

    def _setup_spaces(self):
        """从服务器获取并设置动作空间和观察空间"""
        try:
            # 获取空间定义
            request = simulation_pb2.GetSpacesRequest(scenario=self.scenario)
            response = self.client.GetSpaces(request)

            # 设置action space
            self.action_space = self._convert_proto_space_to_gym(response.action_space)

            # 设置observation space
            self.observation_space = self._convert_proto_space_to_gym(response.observation_space)

            print(f"Scenario '{self.scenario}' loaded:")
            print(f"  Action space: {self.action_space}")
            print(f"  Observation space: {self.observation_space}")

            self._spaces_loaded = True

        except Exception as e:
            print(f"Warning: Could not get spaces from server for scenario '{self.scenario}': {e}")
            print("Using default fallback spaces.")
            # 回退到默认定义
            self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float32)
            self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(1,), dtype=np.float32)
            self._spaces_loaded = False

    def _convert_proto_space_to_gym(self, proto_space) -> gym.Space:
        """将协议空间定义转换为gymnasium空间"""
        if proto_space.type == 0:  # BOX type
            return spaces.Box(
                low=np.array(proto_space.low, dtype=np.float32),
                high=np.array(proto_space.high, dtype=np.float32),
                shape=tuple(proto_space.shape),
                dtype=getattr(np, proto_space.dtype) if proto_space.dtype else np.float32,
            )
        elif proto_space.type == 1:  # DISCRETE type
            # 对于离散空间，使用shape[0]作为n
            n = int(proto_space.shape[0]) if proto_space.shape else 2
            return spaces.Discrete(n)
        elif proto_space.type == 2:  # MULTI_DISCRETE type
            return spaces.MultiDiscrete(proto_space.shape)
        elif proto_space.type == 3:  # MULTI_BINARY type
            return spaces.MultiBinary(proto_space.shape)
        else:
            print(f"Unknown space type: {proto_space.type}, using Box as fallback")
            return spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float32)

    def _create_environment(self):
        """创建环境（如果尚未创建）"""
        if self._env_created:
            return

        # 将配置转换为字符串字典（gRPC要求）
        config_str = {k: str(v) for k, v in self.config.items()}

        request = simulation_pb2.CreateEnvironmentRequest(env_id=self.env_id, scenario=self.scenario, config=config_str)

        response = self.client.CreateEnvironment(request)
        if not response.success:
            raise RuntimeError(f"Failed to create environment '{self.scenario}': {response.message}")

        self._env_created = True
        print(f"Environment created: {self.env_id} (scenario: {self.scenario})")

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        """重置环境"""
        super().reset(seed=seed)

        # 确保环境已创建
        self._create_environment()

        request = simulation_pb2.ResetEnvironmentRequest(env_id=self.env_id)
        response = self.client.ResetEnvironment(request)

        # 解析观察数据
        if not response.observations:
            raise RuntimeError("No observations received from environment reset")

        obs_data = response.observations[0].data
        observation = np.array([float(x) for x in obs_data], dtype=np.float32)

        # 构建info字典，包含服务器返回的所有信息
        info = dict(response.info)

        # 添加一些通用信息
        if len(observation) >= 1:
            info["observation_size"] = len(observation)

        return observation, info

    def step(self, action: Union[int, float, np.ndarray]) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """执行一步"""
        # 将action转换为适当的gRPC格式
        grpc_action = self._convert_action_to_proto(action)

        request = simulation_pb2.StepEnvironmentRequest(env_id=self.env_id, action=grpc_action)
        response = self.client.StepEnvironment(request)

        # 解析响应
        if not response.observations:
            raise RuntimeError("No observations received from environment step")

        obs_data = response.observations[0].data
        observation = np.array([float(x) for x in obs_data], dtype=np.float32)
        reward = float(response.rewards[0]) if response.rewards else 0.0
        terminated = bool(response.done[0]) if response.done else False
        truncated = False  # 可以根据需要扩展

        # 构建info字典
        info = dict(response.info)
        info["action_taken"] = action

        return observation, reward, terminated, truncated, info

    def _convert_action_to_proto(self, action: Union[int, float, np.ndarray]) -> simulation_pb2.Action:
        """将Python action转换为protobuf Action"""
        if isinstance(action, np.ndarray):
            if action.dtype in [np.float32, np.float64]:
                if action.size == 1:
                    return simulation_pb2.Action(float_value=float(action.item()))
                else:
                    return simulation_pb2.Action(float_array=action.astype(np.float64).tolist())
            elif action.dtype in [np.int32, np.int64]:
                if action.size == 1:
                    return simulation_pb2.Action(int_value=int(action.item()))
                else:
                    return simulation_pb2.Action(int_array=action.astype(np.int64).tolist())
            elif action.dtype == np.bool_:
                if action.size == 1:
                    return simulation_pb2.Action(bool_value=bool(action.item()))
                else:
                    return simulation_pb2.Action(bool_array=action.tolist())
        elif isinstance(action, (int, np.integer)):
            return simulation_pb2.Action(int_value=int(action))
        elif isinstance(action, (float, np.floating)):
            return simulation_pb2.Action(float_value=float(action))
        elif isinstance(action, bool):
            return simulation_pb2.Action(bool_value=action)
        elif isinstance(action, str):
            return simulation_pb2.Action(string_value=action)
        elif isinstance(action, (list, tuple)):
            # 尝试推断类型
            if all(isinstance(x, (int, np.integer)) for x in action):
                return simulation_pb2.Action(int_array=list(action))
            elif all(isinstance(x, (float, np.floating)) for x in action):
                return simulation_pb2.Action(float_array=list(action))
            elif all(isinstance(x, bool) for x in action):
                return simulation_pb2.Action(bool_array=list(action))

        # 回退：尝试转换为float
        try:
            return simulation_pb2.Action(float_value=float(action))
        except (ValueError, TypeError):
            raise ValueError(f"Cannot convert action of type {type(action)} to protobuf Action: {action}")

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

    def get_available_scenarios(self) -> list:
        """获取服务器支持的所有场景"""
        try:
            info_request = simulation_pb2.GetInfoRequest()
            response = self.client.GetInfo(info_request)
            return list(response.scenarios)
        except Exception as e:
            print(f"Error getting scenarios: {e}")
            return []


# 向后兼容的环境包装器
class SimpleEnv(GrpcEnv):
    """
    向后兼容的环境包装器
    为了保持与现有代码的兼容性
    """

    def __init__(self, host="127.0.0.1", port=9090, env_id=None, max_steps=50, tolerance=0.5):
        config = {"max_steps": max_steps, "tolerance": tolerance}
        super(SimpleEnv, self).__init__(scenario="default", host=host, port=port, env_id=env_id, config=config)


def test_generic_env():
    """测试通用gRPC环境"""
    print("Testing Generic gRPC Environment...")

    try:
        # 创建通用环境
        env = GrpcEnv(scenario="default", config={"max_steps": 20, "tolerance": 0.3})

        print(f"\nScenario: {env.scenario}")
        print(f"Available scenarios: {env.get_available_scenarios()}")

        # 重置环境
        obs, info = env.reset()
        print(f"Initial observation: {obs}")
        print(f"Initial info: {info}")

        total_reward = 0
        step_count = 0

        # 运行一个episode
        for step in range(20):  # 最大20步
            # 随机动作
            action = env.action_space.sample()

            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            step_count += 1

            print(f"Step {step_count}: action={action}, reward={reward:.3f}, done={terminated}")

            if terminated or truncated:
                print(f"Episode finished! Total reward: {total_reward:.3f}")
                break

        env.close()
        print("Generic environment test completed successfully!")

        # 测试不同类型的action
        print("\n=== Testing different action types ===")
        env2 = GrpcEnv(scenario="default", config={"max_steps": 5})

        obs, _ = env2.reset()

        # 测试不同类型的action
        test_actions = [
            1.5,  # float
            np.array([2.0]),  # numpy array
            np.array([1.0, 2.0]),  # multi-dimensional array
        ]

        for i, action in enumerate(test_actions):
            try:
                obs, reward, terminated, truncated, info = env2.step(action)
                print(f"Action {i+1} ({type(action)}): {action} -> reward: {reward:.3f}")
                if terminated:
                    obs, _ = env2.reset()
            except Exception as e:
                print(f"Action {i+1} failed: {e}")

        env2.close()

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


def test_simple_env():
    """测试兼容环境（向后兼容测试）"""
    print("Testing gRPC Environment...")

    # 创建环境
    env = SimpleEnv(max_steps=20, tolerance=0.3)

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
    print("=== Testing Generic gRPC Environment ===")
    test_generic_env()

    print("\n" + "=" * 50)
    print("=== Testing Environment (Backward Compatibility) ===")
    test_simple_env()
