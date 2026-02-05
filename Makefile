# Makefile for RL Env Engine
# A unified build system for Go server and Python client SDK

.PHONY: help
help:
	@echo "RL Env Engine - Build System"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "=== Proto Generation ==="
	@echo "  proto              Generate protobuf code for Go and Python"
	@echo ""
	@echo "=== Go Commands ==="
	@echo "  build-go           Build Go server"
	@echo "  run-server         Run gRPC server"
	@echo "  run-http           Run HTTP server"
	@echo "  run-dual           Run both HTTP and gRPC servers"
	@echo "  test-go            Run Go tests"
	@echo "  fmt-go             Format Go code"
	@echo "  vet-go             Run go vet"
	@echo "  lint-go            Run golangci-lint"
	@echo "  deps-go            Install Go dependencies"
	@echo ""
	@echo "=== Python Commands ==="
	@echo "  install-python     Install Python package in development mode"
	@echo "  build-python       Build Python wheel"
	@echo "  test-python        Run Python tests"
	@echo "  fmt-python         Format Python code"
	@echo "  lint-python        Lint Python code"
	@echo "  deps-python        Install Python dependencies"
	@echo ""
	@echo "=== All Languages ==="
	@echo "  build              Build everything"
	@echo "  test               Run all tests"
	@echo "  clean              Clean build artifacts"
	@echo "  dev-setup          Set up development environment"
	@echo ""
	@echo "=== Docker ==="
	@echo "  docker-build-go    Build Go Docker image"
	@echo "  docker-build-py    Build Python Docker image"

# ==============================================================================
# Proto Generation
# ==============================================================================

.PHONY: proto
proto:
	@echo "Generating protobuf code..."
	./scripts/gen_proto.sh

# ==============================================================================
# Go Commands
# ==============================================================================

GO_MODULE := github.com/jelech/rl_env_engine/go
GO_DIR := ./go
GO_BIN_DIR := ./bin

.PHONY: build-go
build-go:
	@echo "Building Go server..."
	@mkdir -p $(GO_BIN_DIR)
	cd $(GO_DIR) && go build -o ../$(GO_BIN_DIR)/server ./cmd/server

.PHONY: run-server
run-server:
	@echo "Starting gRPC server..."
	cd $(GO_DIR) && go run ./cmd/server

.PHONY: run-http
run-http:
	@echo "Starting HTTP server..."
	cd $(GO_DIR) && go run ./cmd/http-server 2>/dev/null || echo "HTTP server not implemented yet"

.PHONY: run-dual
run-dual:
	@echo "Starting dual servers (HTTP + gRPC)..."
	cd $(GO_DIR) && go run ./cmd/dual-server 2>/dev/null || echo "Dual server not implemented yet"

.PHONY: test-go
test-go:
	@echo "Running Go tests..."
	cd $(GO_DIR) && go test ./...

.PHONY: fmt-go
fmt-go:
	@echo "Formatting Go code..."
	cd $(GO_DIR) && go fmt ./...

.PHONY: vet-go
vet-go:
	@echo "Running go vet..."
	cd $(GO_DIR) && go vet ./...

.PHONY: lint-go
lint-go:
	@echo "Running golangci-lint..."
	cd $(GO_DIR) && golangci-lint run

.PHONY: deps-go
deps-go:
	@echo "Installing Go dependencies..."
	cd $(GO_DIR) && go mod download && go mod tidy

# ==============================================================================
# Python Commands
# ==============================================================================

PYTHON_DIR := ./python

.PHONY: install-python
install-python:
	@echo "Installing Python package in development mode..."
	pip install -e "$(PYTHON_DIR)[dev]"

.PHONY: build-python
build-python:
	@echo "Building Python wheel..."
	cd $(PYTHON_DIR) && python -m build

.PHONY: test-python
test-python:
	@echo "Running Python tests..."
	cd $(PYTHON_DIR) && pytest

.PHONY: fmt-python
fmt-python:
	@echo "Formatting Python code..."
	cd $(PYTHON_DIR) && black src && isort src

.PHONY: lint-python
lint-python:
	@echo "Linting Python code..."
	cd $(PYTHON_DIR) && ruff check src

.PHONY: deps-python
deps-python:
	@echo "Installing Python dependencies..."
	pip install -e "$(PYTHON_DIR)[dev,rl]"

# ==============================================================================
# Combined Commands
# ==============================================================================

.PHONY: build
build: proto build-go build-python
	@echo "Build complete!"

.PHONY: test
test: test-go test-python
	@echo "All tests passed!"

.PHONY: clean
clean:
	@echo "Cleaning build artifacts..."
	rm -rf $(GO_BIN_DIR)
	rm -rf $(PYTHON_DIR)/dist
	rm -rf $(PYTHON_DIR)/build
	rm -rf $(PYTHON_DIR)/*.egg-info
	rm -rf $(PYTHON_DIR)/src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	cd $(GO_DIR) && go clean 2>/dev/null || true
	@echo "Clean complete!"

.PHONY: dev-setup
dev-setup: deps-go deps-python proto
	@echo "Development environment setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Run 'make run-server' to start the gRPC server"
	@echo "  2. In another terminal, run Python client:"
	@echo "     python -c 'from rl_env_engine.client import GrpcEnv; print(\"SDK loaded!\")'"

# ==============================================================================
# Docker Commands
# ==============================================================================

DOCKER_REGISTRY ?= 
DOCKER_TAG ?= latest

.PHONY: docker-build-go
docker-build-go:
	@echo "Building Go Docker image..."
	docker build -f Dockerfile.go -t $(DOCKER_REGISTRY)rl-env-engine-server:$(DOCKER_TAG) .

.PHONY: docker-build-py
docker-build-py:
	@echo "Building Python Docker image..."
	docker build -f Dockerfile.py -t $(DOCKER_REGISTRY)rl-env-engine-python:$(DOCKER_TAG) .

# ==============================================================================
# Legacy Commands (for backward compatibility during migration)
# ==============================================================================

.PHONY: proto-old
proto-old:
	@echo "Using legacy proto generation..."
	./gen_grpc.sh 2>/dev/null || echo "Legacy script not found, use 'make proto' instead"
