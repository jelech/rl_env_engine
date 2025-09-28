# Makefile for Simulations Framework


.PHONY: help
help:
	@echo "可用的make命令:"
	@echo "help             : 显示此帮助信息"
	@echo "---------------- 构建 ----------------"
	@echo "build            : 构建所有示例 (HTTP / gRPC / Dual)"
	@echo "build-server     : 仅构建 HTTP 服务器示例"
	@echo "build-grpc       : 仅构建 gRPC 服务器示例"
	@echo "build-dual       : 构建双协议服务器示例"
	@echo "build-grpc-test  : 构建 gRPC 测试客户端示例"
	@echo "build-simple-test: 构建简单场景测试示例"
	@echo "build-grpc-all   : 构建所有 gRPC 相关示例"
	@echo "all              : 清理 + 格式化 + 静态检查 + 构建"
	@echo "---------------- 运行 ----------------"
	@echo "run-server       : 运行 HTTP 服务器"
	@echo "run-grpc         : 运行 gRPC 服务器"
	@echo "run-dual         : 运行双协议服务器"
	@echo "server-bg        : 后台启动 HTTP 服务器 (输出到 server.log)"
	@echo "server-stop      : 停止后台运行的 HTTP 服务器"
	@echo "dev              : 开发模式运行 HTTP 服务器"
	@echo "dev-grpc         : 开发模式运行 gRPC 服务器(使用已构建的二进制)"
	@echo "---------------- 演示流程 --------------"
	@echo "demo-http        : 演示 HTTP 启动/测试/停止流程"
	@echo "demo-grpc        : 演示 gRPC 启动/测试/停止流程"
	@echo "demo-dual        : 演示 双协议 启动/测试/停止流程"
	@echo "---------------- 测试 ----------------"
	@echo "test             : 运行 Go 测试"
	@echo "test-python      : 测试 Python HTTP API 客户端"
	@echo "test-grpc-python : 测试 Python gRPC 客户端"
	@echo "test-grpc-quick  : 快速构建并测试 gRPC (Go)"
	@echo "test-python-sb3  : 启动 gRPC 并运行 Python SB3 测试"
	@echo "---------------- 代码质量 --------------"
	@echo "fmt              : Go 代码格式化"
	@echo "vet              : 运行 go vet"
	@echo "lint             : 运行 golangci-lint"
	@echo "clean            : 清理构建产物"
	@echo "status           : 显示项目状态 (Go 版本 / 模块 / 文件)"
	@echo "---------------- 依赖与生成 ------------"
	@echo "deps             : 安装 Go 依赖 (download + tidy)"
	@echo "python-deps      : 安装 Python HTTP 客户端依赖"
	@echo "python-grpc-deps : 安装 Python gRPC 依赖"
	@echo "python-sb3-setup : 安装 Python SB3 相关依赖"
	@echo "proto            : 生成 Go Protobuf 代码"
	@echo "proto-python     : 生成 Python Protobuf 代码"
	@echo "dev-setup        : 一次性完成开发环境初始化 (Go/Python/Proto)"

# 构建示例程序
build:
	@echo "Building server example..."
	go build -o bin/server_example examples/server/main.go
	@echo "Building gRPC server example..."
	go build -o bin/grpc_server_example examples/grpc_server/main.go
	@echo "Building dual server example..."
	go build -o bin/dual_server_example examples/dual_server/main.go


# 构建服务器示例
build-server:
	@echo "Building server example..."
	go build -o bin/server_example examples/server/main.go

# 构建gRPC服务器示例
build-grpc:
	@echo "Building gRPC server example..."
	go build -o bin/grpc_server_example examples/grpc_server/main.go

# 构建双服务器示例
build-dual:
	@echo "Building dual server example..."
	go build -o bin/dual_server_example examples/dual_server/main.go

# 运行测试
test:
	@echo "Running tests..."
	go test ./...

# 清理构建文件
clean:
	@echo "Cleaning..."
	rm -rf bin/
	go clean


# 运行服务器示例
run-server:
	@echo "Starting HTTP simulation server..."
	go run examples/server/main.go

# 运行gRPC服务器示例
run-grpc:
	@echo "Starting gRPC simulation server..."
	go run examples/grpc_server/main.go

# 运行双服务器示例（HTTP + gRPC）
run-dual:
	@echo "Starting dual simulation servers (HTTP + gRPC)..."
	go run examples/dual_server/main.go

# 运行服务器（后台模式）
server-bg:
	@echo "Starting simulation server in background..."
	nohup go run examples/server/main.go > server.log 2>&1 &
	@echo "Server started in background. Check server.log for output."

# 停止后台服务器
server-stop:
	@echo "Stopping background server..."
	pkill -f "examples/server/main.go" || echo "No server process found"

# 生成protobuf文件
proto:
	@echo "Generating protobuf files..."
	./generate_proto.sh

# 生成Python protobuf文件
proto-python:
	@echo "Generating Python protobuf files..."
	./generate_python_proto.sh

# 测试Python API连接
test-python:
	@echo "Testing Python HTTP API connection..."
	cd python_client && python test_api.py

# 测试Python gRPC连接
test-grpc-python:
	@echo "Testing Python gRPC connection..."
	cd python_client && python grpc_client.py

# 代码格式化
fmt:
	@echo "Formatting code..."
	go fmt ./...

# 静态分析
vet:
	@echo "Running go vet..."
	go vet ./core/... ./scenarios/... ./server/... ./examples/...

# 代码检查
lint:
	@echo "Running golangci-lint..."
	golangci-lint run

# 安装依赖
deps:
	@echo "Installing dependencies..."
	go mod download
	go mod tidy

# 安装Python依赖
python-deps:
	@echo "Installing Python dependencies..."
	cd python_client && pip install -r requirements.txt

# 安装Python gRPC依赖
python-grpc-deps:
	@echo "Installing Python gRPC dependencies..."
	cd python_client && pip install -r requirements_grpc.txt

# 创建构建目录
bin:
	mkdir -p bin

# 完整构建
all: clean fmt vet bin build
	@echo "Build completed successfully!"

# 开发环境设置
dev-setup: deps python-deps python-grpc-deps proto proto-python
	@echo "Development environment setup completed!"

# 演示HTTP API流程
demo-http: build-server
	@echo "Starting HTTP API demo..."
	@echo "1. Starting HTTP server in background..."
	@make server-bg
	@sleep 3
	@echo "2. Testing HTTP API connection..."
	@make test-python
	@echo "3. Stopping server..."
	@make server-stop
	@echo "HTTP API demo completed!"

# 演示gRPC API流程
demo-grpc: build-grpc
	@echo "Starting gRPC API demo..."
	@echo "1. Starting gRPC server in background..."
	nohup go run examples/grpc_server/main.go > grpc_server.log 2>&1 &
	@sleep 3
	@echo "2. Testing gRPC API connection..."
	@make test-grpc-python
	@echo "3. Stopping gRPC server..."
	pkill -f "examples/grpc_server/main.go" || echo "No gRPC server process found"
	@echo "gRPC API demo completed!"

# 演示双服务器流程
demo-dual: build-dual
	@echo "Starting dual servers demo..."
	@echo "1. Starting both HTTP and gRPC servers in background..."
	nohup go run examples/dual_server/main.go > dual_server.log 2>&1 &
	@sleep 3
	@echo "2. Testing HTTP API connection..."
	@make test-python
	@echo "3. Testing gRPC API connection..."
	@make test-grpc-python
	@echo "4. Stopping servers..."
	pkill -f "examples/dual_server/main.go" || echo "No dual server process found"
	@echo "Dual servers demo completed!"

# 开发模式：启动服务器并测试
dev: run-server

# 开发模式：启动gRPC服务器进行SB3开发
dev-grpc: build-grpc
	@echo "Starting gRPC server for SB3 development..."
	./bin/grpc_server_example

# 快速测试：构建并测试gRPC环境
test-grpc-quick: build-grpc build-grpc-test
	@echo "Starting gRPC server in background..."
	@nohup ./bin/grpc_server_example > grpc_server.log 2>&1 &
	@sleep 3
	@echo "Testing gRPC environment..."
	@./bin/grpc_test_example
	@echo "Stopping gRPC server..."
	@pkill -f grpc_server_example || echo "No gRPC server process found"
	@echo "gRPC test completed!"

# 构建所有gRPC相关示例
build-grpc-all: build-grpc build-grpc-test build-simple-test
	@echo "All gRPC examples built successfully!"

# 构建gRPC测试客户端
build-grpc-test:
	@echo "Building gRPC test client..."
	go build -o bin/grpc_test_example examples/grpc_test/main.go

# 构建简单场景测试
build-simple-test:
	@echo "Building simple scenario test..."
	go build -o bin/simple_test_example examples/simple_test/main.go

# Python SB3相关命令
python-sb3-setup: proto-python python-grpc-deps
	@echo "Setting up Python SB3 environment..."
	@echo "Installing additional SB3 dependencies..."
	cd python_client && pip install stable-baselines3[extra] gymnasium matplotlib tensorboard

# 测试Python SB3环境
test-python-sb3: build-grpc
	@echo "Starting gRPC server for Python SB3 test..."
	@nohup ./bin/grpc_server_example > grpc_server.log 2>&1 &
	@sleep 3
	@echo "Running Python SB3 environment test..."
	cd python_client && python comprehensive_test.py
	@echo "Stopping gRPC server..."
	@pkill -f grpc_server_example || echo "No gRPC server process found"

# 查看项目状态
status:
	@echo "Project status:"
	@echo "Go version: $(shell go version)"
	@echo "Module: $(shell head -1 go.mod)"
	@echo "Files structure:"
	@find . -name "*.go" -not -path "./.git/*" | sort
