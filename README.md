# RL Env Engine

A flexible simulation framework for reinforcement learning with multi-language SDK support.

## Project Structure

```
rl_env_engine/
├── api/                          # Protocol definitions (source of truth)
│   ├── openapi/
│   │   └── v1/
│   │       └── simulation.yaml # OpenAPI/Swagger definition
│   └── proto/
│       └── v1/
│           └── simulation.proto  # gRPC service definition
│
├── go/                           # Go module (independent)
│   ├── go.mod                    # github.com/jelech/rl_env_engine/go
│   ├── cmd/
│   │   └── server/               # gRPC server entry point
│   ├── internal/                 # Private implementation
│   │   ├── server/               # Server implementation
│   │   └── scenarios/            # Built-in scenarios
│   └── pkg/                      # Public SDK
│       ├── api/v1/               # Generated protobuf code
│       ├── client/               # Go Client SDK
│       ├── core/                 # Core interfaces
│       └── sdk/                  # Server SDK
│
├── python/                       # Python package (independent)
│   ├── pyproject.toml            # rl-env-engine
│   ├── README.md
│   └── src/
│       └── rl_env_engine/
│           ├── client/           # Python Client SDK
│           └── generated/        # Generated protobuf code
│
├── scripts/
│   └── gen_proto.sh              # Generate Go + Python code
│
├── Makefile                      # Unified build system
└── README.md
```

## Quick Start

### 1. Setup Development Environment

```bash
make dev-setup
```

### 2. Generate Protobuf Code

```bash
make proto
```

### 3. Run Server

```bash
make run-server
```

### 4. Use Python Client

```python
from rl_env_engine.client import GrpcEnv

env = GrpcEnv(scenario="cartpole", host="127.0.0.1", port=9090)
obs, info = env.reset()

for _ in range(100):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    if terminated or truncated:
        obs, info = env.reset()

env.close()
```

## Installation

### Local Development Installation

If you want to use the framework in your local projects without publishing to PyPI:

```bash
# 1. Navigate to the python directory
cd python

# 2. Install in editable mode
pip install -e .
```

This allows you to import `rl_env_engine` in your other projects while keeping the ability to modify the source code.

### Go SDK

```bash
# Server SDK (for implementing new scenarios)
go get github.com/jelech/rl_env_engine/go/pkg/sdk@latest

# Client SDK (for connecting to servers)
go get github.com/jelech/rl_env_engine/go/pkg/client@latest
```

### Python SDK

```bash
# Basic installation
pip install rl-env-engine

# With RL dependencies (stable-baselines3, torch, etc.)
pip install rl-env-engine[rl]
```

## Git Workflow

To push your changes to a remote repository (e.g., GitHub):

```bash
# 1. Initialize git repository (if not already done)
git init

# 2. Add remote repository
git remote add origin https://github.com/yourusername/rl_env_engine.git

# 3. Stage and commit changes
git add .
git commit -m "Initial commit"

# 4. Push to GitHub
git push -u origin main
```

## Available Make Commands

```bash
make help          # Show all available commands

# Proto generation
make proto         # Generate Go and Python protobuf code

# Go commands
make build-go      # Build Go server
make run-server    # Run gRPC server
make test-go       # Run Go tests

# Python commands
make install-python  # Install Python package
make build-python    # Build Python wheel
make test-python     # Run Python tests

# Combined
make build         # Build everything
make test          # Run all tests
make clean         # Clean build artifacts
```

## Built-in Scenarios

- **simple**: Mathematical test scenario for debugging
- **cartpole**: Classic CartPole control environment

## Creating Custom Scenarios

Implement the `core.Scenario` interface:

```go
import "github.com/jelech/rl_env_engine/go/pkg/core"

type MyScenario struct {
    name string
}

func (s *MyScenario) GetName() string { return s.name }
func (s *MyScenario) GetDescription() string { return "My custom scenario" }
func (s *MyScenario) CreateEnvironment(config core.Config) (core.Environment, error) {
    // Create and return your environment
}
func (s *MyScenario) ValidateConfig(config core.Config) error {
    // Validate configuration
}
```

## License

MIT
