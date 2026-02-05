# RL Env Engine - Python SDK

Python SDK for RL Env Engine, providing both Client and Server capabilities for reinforcement learning environments.

## Installation

```bash
# Basic installation (Client SDK only)
pip install rl-env-engine

# With Server SDK (FastAPI, Redis, etc.)
pip install rl-env-engine[server]

# With RL dependencies (stable-baselines3, torch, etc.)
pip install rl-env-engine[rl]

# All features
pip install rl-env-engine[all]

# Development installation
pip install -e ".[dev]"
```

## Quick Start

### 1. Gymnasium-style Environment

```python
from rl_env_engine.client import GrpcEnv

# Connect to gRPC server
env = GrpcEnv(
    scenario="cartpole",
    host="127.0.0.1",
    port=9090,
    config={"max_steps": 500}
)

# Standard Gymnasium interface
obs, info = env.reset()
for _ in range(100):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        obs, info = env.reset()

env.close()
```

### 2. Batch Execution with Service Discovery

```python
from rl_env_engine.client import SimulationSDK

# Connect to service discovery endpoint
sdk = SimulationSDK(discovery_url="http://localhost:8000/ips")

# Create sessions on available workers
sdk.create_sessions(
    batch_size=4,
    scenario="my_scenario",
    config={"param": "value"},
    data_dir="/path/to/data",  # Optional: load multi-date data
)

# Batch execution with queue scheduling
import torch
actions = [torch.randn(10) for _ in range(10)]  # More actions than workers
results = sdk.batch_step(actions)  # Automatically queued

sdk.close()
```

### 3. Create Your Own Server

```python
from rl_env_engine.server import create_app, BaseScenario, run_server

class MyScenario(BaseScenario):
    @property
    def name(self):
        return "my_scenario"
    
    def create_environment(self, config):
        return {"state": 0, "config": config}
    
    def reset(self, env, **kwargs):
        env["state"] = 0
        return {"observation": [0.0], "info": {}}
    
    def step(self, env, action, **kwargs):
        env["state"] += action.get("value", 1)
        return {
            "observation": [float(env["state"])],
            "reward": 1.0,
            "done": env["state"] >= 10,
            "info": {},
        }

# Create and run server
app = create_app(
    scenarios=[MyScenario()],
    scenario_name="my_service",
    enable_discovery=True,  # Register with Redis
)
run_server(app, port=8000)
```

### 4. Train with Stable-Baselines3

```python
from stable_baselines3 import PPO
from rl_env_engine.client import GrpcEnv

env = GrpcEnv(scenario="cartpole", host="127.0.0.1", port=9090)

model = PPO("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=10000)

env.close()
```

## Package Structure

```
rl_env_engine/
├── __init__.py              # Package exports
├── client/                  # Client SDK
│   ├── grpc_client.py       # Low-level gRPC client
│   ├── grpc_env.py          # Gymnasium wrapper
│   ├── local_env.py         # Local .so wrapper
│   └── sdk.py               # High-level SDK (discovery, batch)
├── server/                  # Server SDK
│   ├── fastapi_server.py    # FastAPI server framework
│   ├── discovery.py         # Redis service discovery
│   └── task_manager.py      # Async task management
└── generated/               # Auto-generated protobuf code
```

## API Reference

### Client SDK

| Class | Description |
|-------|-------------|
| `GrpcEnv` | Gymnasium-compatible environment wrapper |
| `SimulationGrpcClient` | Low-level gRPC client |
| `SimulationSDK` | High-level SDK with service discovery |
| `LocalEnv` | Local Go shared library wrapper |

### Server SDK

| Class/Function | Description |
|----------------|-------------|
| `create_app()` | Create FastAPI application |
| `BaseScenario` | Abstract base class for scenarios |
| `ServiceDiscovery` | Redis-based service discovery |
| `TaskManager` | Async task management |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `ADVERTISED_IP` | Public IP for service discovery | Auto-detect |
| `ADVERTISED_PORT` | Public port for service discovery | From `PORT` |
| `PORT` | Server port | `8000` |

## License

MIT
