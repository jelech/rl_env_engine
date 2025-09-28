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
        verbose: bool = False,
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
        self.verbose = verbose

        # 连接到服务器
        self._connect()

        # 创建环境
        self._create_environment()

        # 获取空间定义
        self._setup_spaces()

    def verbose_print(self, *args, **kwargs):
        if self.verbose:
            print(*args, **kwargs)

    def _connect(self):
        """连接到gRPC服务器"""
        try:
            self.channel = grpc.insecure_channel(f"{self.host}:{self.port}")
            self.client = simulation_pb2_grpc.SimulationServiceStub(self.channel)

            # 测试连接
            info_request = simulation_pb2.GetInfoRequest()
            self.client.GetInfo(info_request)

        except Exception as e:
            raise ConnectionError(f"Failed to connect to gRPC server at {self.host}:{self.port}: {e}")

    def _setup_spaces(self):
        """从服务器获取并设置动作空间和观察空间"""
        try:
            request = simulation_pb2.GetSpacesRequest(env_id=self.env_id)
            response = self.client.GetSpaces(request)

            self.action_space = self._convert_proto_space_to_gym(response.action_space)
            self.observation_space = self._convert_proto_space_to_gym(response.observation_space)

            self.verbose_print(f"Scenario '{self.scenario}' loaded:")
            self.verbose_print(f"  Action space: {self.action_space}")
            self.verbose_print(f"  Observation space: {self.observation_space}")

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
        self.verbose_print(f"Environment created: {self.env_id} (scenario: {self.scenario})")

    def get_spaces(self) -> Tuple[gym.Space, gym.Space]:
        """获取动作空间和观察空间"""
        if not self._spaces_loaded:
            self._setup_spaces()
        return self.action_space, self.observation_space

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

    def step(self, action: Union[int, float, np.ndarray, list]) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """执行一步"""
        # 将action转换为gRPC格式（支持多动作）
        grpc_actions = self._convert_actions_to_proto(action)

        request = simulation_pb2.StepEnvironmentRequest(env_id=self.env_id, actions=grpc_actions)
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
        info["num_actions"] = len(grpc_actions)

        return observation, reward, terminated, truncated, info

    def _convert_single_action_to_proto_cached(self, action):
        """带缓存的动作转换（适用于离散动作）"""
        if isinstance(action, (int, float, bool)) and len(self._action_cache) < self._max_cache_size:
            cache_key = (type(action), action)
            if cache_key not in self._action_cache:
                self._action_cache[cache_key] = self._convert_single_action_to_proto(action)
            return self._action_cache[cache_key]

        return self._convert_single_action_to_proto(action)

    def _convert_actions_to_proto(self, actions: Union[int, float, np.ndarray, list]) -> list:
        """将Python actions转换为protobuf Action列表"""
        if not isinstance(actions, (list, tuple)):
            # 单个动作，包装成列表
            return [self._convert_single_action_to_proto_cached(actions)]

        # 多动作列表
        return [self._convert_single_action_to_proto_cached(action) for action in actions]

    def _convert_single_action_to_proto(self, action: Union[int, float, np.ndarray]) -> simulation_pb2.Action:
        """将单个Python action转换为protobuf Action"""
        # numpy数组处理
        if isinstance(action, np.ndarray):
            return self._handle_numpy_action(action)

        # 基本类型处理
        if isinstance(action, (int, np.integer)):
            return simulation_pb2.Action(int_value=int(action))
        elif isinstance(action, (float, np.floating)):
            return simulation_pb2.Action(float_value=float(action))
        elif isinstance(action, bool):
            return simulation_pb2.Action(bool_value=action)
        elif isinstance(action, str):
            return simulation_pb2.Action(string_value=action)

        # 列表/元组处理
        if isinstance(action, (list, tuple)):
            return self._handle_sequence_action(action)

        # 回退处理
        return self._fallback_action_conversion(action)

    def _handle_numpy_action(self, action: np.ndarray) -> simulation_pb2.Action:
        """处理numpy数组动作"""
        if action.size == 1:
            # 单元素数组，提取标量值
            scalar = action.item()
            if action.dtype in [np.float32, np.float64]:
                return simulation_pb2.Action(float_value=float(scalar))
            elif action.dtype in [np.int32, np.int64]:
                return simulation_pb2.Action(int_value=int(scalar))
            elif action.dtype == np.bool_:
                return simulation_pb2.Action(bool_value=bool(scalar))
        else:
            # 多元素数组
            if action.dtype in [np.float32, np.float64]:
                return simulation_pb2.Action(
                    float_array=simulation_pb2.FloatArray(values=action.astype(np.float64).tolist())
                )
            elif action.dtype in [np.int32, np.int64]:
                return simulation_pb2.Action(int_array=simulation_pb2.IntArray(values=action.astype(np.int64).tolist()))
            elif action.dtype == np.bool_:
                return simulation_pb2.Action(bool_array=simulation_pb2.BoolArray(values=action.tolist()))

        # 回退：尝试转float数组
        return simulation_pb2.Action(float_array=simulation_pb2.FloatArray(values=action.astype(np.float64).tolist()))

    def _handle_sequence_action(self, action: Union[list, tuple]) -> simulation_pb2.Action:
        """处理列表/元组动作"""
        if not action:
            raise ValueError("Empty action sequence")

        # 类型检查并转换
        if all(isinstance(x, (int, np.integer)) for x in action):
            return simulation_pb2.Action(int_array=simulation_pb2.IntArray(values=[int(x) for x in action]))
        elif all(isinstance(x, (float, np.floating)) for x in action):
            return simulation_pb2.Action(float_array=simulation_pb2.FloatArray(values=[float(x) for x in action]))
        elif all(isinstance(x, bool) for x in action):
            return simulation_pb2.Action(bool_array=simulation_pb2.BoolArray(values=list(action)))
        else:
            # 混合类型，尝试转换为float数组
            try:
                float_values = [float(x) for x in action]
                return simulation_pb2.Action(float_array=simulation_pb2.FloatArray(values=float_values))
            except (ValueError, TypeError):
                raise ValueError(f"Cannot convert mixed-type action to uniform array: {action}")

    def _fallback_action_conversion(self, action) -> simulation_pb2.Action:
        """回退动作转换"""
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
                self.verbose_print(f"Environment closed: {response.message}")
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
