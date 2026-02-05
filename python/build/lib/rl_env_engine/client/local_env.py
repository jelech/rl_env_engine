import ctypes
import json
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import Dict, Any, Optional, Union, Tuple
import os


class LocalEnv(gym.Env):
    """
    使用 ctypes 调用 C 共享库 (.so) 的本地环境包装器。
    在同一进程中直接连接到 Go 环境引擎。
    """

    metadata = {"render.modes": ["human"]}

    def __init__(
        self,
        lib_path: str,
        scenario: str,
        config: Optional[Dict[str, Any]] = None,
        env_id: Optional[str] = None,
        auto_reset: bool = True,
    ):
        """
        初始化本地环境。

        参数:
            lib_path: 已编译的 .so 库的路径(例如"libsimulations.so")
            scenario: 要创建的场景的名称(例如"CacheOrder")
            config: 环境的配置字典
            env_id: 可选 ID(在本地模式下未使用，但为了兼容性而保留)
            auto_reset: 是否自动重置
        """
        if not os.path.exists(lib_path):
            raise FileNotFoundError(f"Shared library not found at: {lib_path}")

        self.lib = ctypes.CDLL(lib_path)

        # Define function signatures
        self.lib.CreateEnv.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self.lib.CreateEnv.restype = ctypes.c_int

        self.lib.Reset.argtypes = [ctypes.c_int]
        self.lib.Reset.restype = ctypes.c_int

        self.lib.Step.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int,
            ctypes.c_int,
        ]
        self.lib.Step.restype = ctypes.c_int

        self.lib.GetObservation.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int,
        ]
        self.lib.GetObservation.restype = ctypes.c_int

        self.lib.GetReward.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int,
        ]
        self.lib.GetReward.restype = ctypes.c_int

        self.lib.GetDone.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_byte),
            ctypes.c_int,
        ]
        self.lib.GetDone.restype = ctypes.c_int

        self.lib.GetSpacesJSON.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_char),
            ctypes.c_int,
        ]
        self.lib.GetSpacesJSON.restype = ctypes.c_int

        self.lib.CloseEnv.argtypes = [ctypes.c_int]
        self.lib.CloseEnv.restype = None

        self.scenario = scenario
        self.config = config or {}
        self.num_agents = 1

        # Create environment
        cfg_str = json.dumps(self.config).encode("utf-8")
        name_str = scenario.encode("utf-8")
        self.id = self.lib.CreateEnv(name_str, cfg_str)
        if self.id < 0:
            raise RuntimeError(
                f"Failed to create environment '{scenario}' with config {self.config}. Error code: {self.id}"
            )

        # Pre-allocate buffers
        self.max_obs_len = 100000
        self.obs_buffer = (ctypes.c_double * self.max_obs_len)()
        self.reward_buffer = (ctypes.c_double * self.max_obs_len)()
        self.done_buffer = (ctypes.c_byte * self.max_obs_len)()

        # Setup spaces from Go side
        self._setup_spaces()

        if auto_reset:
            self.reset()

    def _setup_spaces(self):
        """从Go端获取并设置Space"""
        max_len = 1024 * 1024
        buf = ctypes.create_string_buffer(max_len)

        length = self.lib.GetSpacesJSON(self.id, buf, max_len)
        if length < 0:
            print(
                f"Warning: Failed to get spaces from environment (code {length}). Using default Box spaces."
            )
            self.action_space = spaces.Box(
                low=-1e9, high=1e9, shape=(1,), dtype=np.float32
            )
            self.observation_space = spaces.Box(
                low=-np.inf, high=np.inf, shape=(1,), dtype=np.float32
            )
            return

        try:
            json_str = buf.value.decode("utf-8")
            space_def = json.loads(json_str)
            self.action_space = self._convert_space_to_gym(
                space_def.get("ActionSpace"), is_action=True
            )
            self.observation_space = self._convert_space_to_gym(
                space_def.get("ObservationSpace"), is_action=False
            )
        except Exception as e:
            print(
                f"Warning: Failed to parse spaces JSON: {e}. Using default Box spaces."
            )
            self.action_space = spaces.Box(
                low=-1e9, high=1e9, shape=(1,), dtype=np.float32
            )
            self.observation_space = spaces.Box(
                low=-np.inf, high=np.inf, shape=(1,), dtype=np.float32
            )

    def _convert_space_to_gym(self, space_dict, is_action=False):
        if not space_dict:
            return spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float32)

        space_type = space_dict.get("Type", 0)
        shape = tuple(space_dict.get("Shape") or [1])

        if space_type == 0:  # Box
            low_list = space_dict.get("Low")
            high_list = space_dict.get("High")

            if not low_list:
                low = np.full(
                    shape, -np.inf if not is_action else -1e9, dtype=np.float32
                )
            else:
                low = np.array(low_list, dtype=np.float32)

            if not high_list:
                high = np.full(
                    shape, np.inf if not is_action else 1e9, dtype=np.float32
                )
            else:
                high = np.array(high_list, dtype=np.float32)

            if low.size == 1 and np.prod(shape) > 1:
                low = np.full(shape, low.item())
            if high.size == 1 and np.prod(shape) > 1:
                high = np.full(shape, high.item())

            if low.shape != shape:
                low = np.resize(low, shape)
            if high.shape != shape:
                high = np.resize(high, shape)

            return spaces.Box(low=low, high=high, shape=shape, dtype=np.float32)

        elif space_type == 1:  # Discrete
            n = int(shape[0]) if shape else 2
            return spaces.Discrete(n)

        elif space_type == 2:  # MultiDiscrete
            return spaces.MultiDiscrete(shape)

        elif space_type == 3:  # MultiBinary
            return spaces.MultiBinary(shape)

        return spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float32)

    def reset(
        self, seed: Optional[int] = None, options: Optional[Dict] = None
    ) -> Tuple[np.ndarray, Dict]:
        super().reset(seed=seed)

        obs_len = self.lib.Reset(self.id)
        if obs_len < 0:
            raise RuntimeError(
                f"Failed to reset environment {self.id}. Error code: {obs_len}"
            )

        count = self.lib.GetObservation(self.id, self.obs_buffer, self.max_obs_len)
        obs = np.array(self.obs_buffer[:count], dtype=np.float32)

        single_obs_size = np.prod(self.observation_space.shape)
        if single_obs_size > 0:
            self.num_agents = int(len(obs) // single_obs_size)
            if self.num_agents == 0:
                self.num_agents = 1
        else:
            self.num_agents = 1

        if self.num_agents > 1:
            old_obs_shape = self.observation_space.shape
            new_obs_shape = (self.num_agents * int(np.prod(old_obs_shape)),)
            self.observation_space = spaces.Box(
                low=np.tile(self.observation_space.low.flatten(), self.num_agents),
                high=np.tile(self.observation_space.high.flatten(), self.num_agents),
                shape=new_obs_shape,
                dtype=self.observation_space.dtype,
            )

            if isinstance(self.action_space, spaces.Box):
                old_act_shape = self.action_space.shape
                new_act_shape = (self.num_agents * int(np.prod(old_act_shape)),)
                self.action_space = spaces.Box(
                    low=np.tile(self.action_space.low.flatten(), self.num_agents),
                    high=np.tile(self.action_space.high.flatten(), self.num_agents),
                    shape=new_act_shape,
                    dtype=self.action_space.dtype,
                )
            elif isinstance(self.action_space, spaces.Discrete):
                self.action_space = spaces.MultiDiscrete(
                    [self.action_space.n] * self.num_agents
                )

        return obs, {}

    def step(
        self, action: Union[int, float, np.ndarray, list]
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, bool, Dict]:
        if isinstance(action, (int, float, np.integer, np.floating)):
            act_list = [float(action)]
        elif isinstance(action, (list, tuple)):
            act_list = []
            for item in action:
                if isinstance(item, (list, tuple, np.ndarray)):
                    if hasattr(item, "flatten"):
                        act_list.extend(item.astype(np.float64).flatten().tolist())
                    else:
                        act_list.extend([float(x) for x in item])
                else:
                    act_list.append(float(item))
        elif isinstance(action, np.ndarray):
            act_list = action.astype(np.float64).flatten().tolist()
        else:
            try:
                act_list = [float(action)]
            except:
                raise ValueError(f"Unsupported action type: {type(action)}")

        c_act = (ctypes.c_double * len(act_list))(*act_list)

        res = self.lib.Step(self.id, c_act, len(act_list), self.num_agents)
        if res < 0:
            raise RuntimeError(
                f"Failed to step environment {self.id}. Error code: {res}"
            )

        obs_count = self.lib.GetObservation(self.id, self.obs_buffer, self.max_obs_len)
        obs = np.array(self.obs_buffer[:obs_count], dtype=np.float32)

        rew_count = self.lib.GetReward(
            self.id, self.reward_buffer, self.max_obs_len
        )
        rewards = np.array(self.reward_buffer[:rew_count], dtype=np.float32)

        done_count = self.lib.GetDone(self.id, self.done_buffer, self.max_obs_len)
        terminated = np.array(
            [bool(self.done_buffer[i]) for i in range(done_count)], dtype=bool
        )

        truncated = False

        if self.num_agents > 1:
            total_reward = float(np.sum(rewards))
            any_terminated = bool(np.any(terminated))
            return (
                obs,
                total_reward,
                any_terminated,
                truncated,
                {"original_rewards": rewards},
            )

        if self.num_agents == 1:
            return (
                obs,
                float(rewards[0]) if len(rewards) > 0 else 0.0,
                bool(terminated[0]) if len(terminated) > 0 else False,
                truncated,
                {},
            )

        return obs, rewards, terminated, truncated, {}

    def close(self):
        if hasattr(self, "id") and self.id >= 0:
            self.lib.CloseEnv(self.id)
            self.id = -1
