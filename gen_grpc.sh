#!/bin/bash

# 生成Python gRPC客户端代码
# 确保安装了必要的包：pip install grpcio-tools

echo "Generating Python protobuf files..."

# 切换到项目根目录
cd "$(dirname "$0")"

# 生成Python protobuf代码
python3 -m grpc_tools.protoc \
    --python_out=python_client/rl_env_engine_client \
    --grpc_python_out=python_client/rl_env_engine_client \
    -I proto \
    proto/simulation.proto

if [ $? -eq 0 ]; then
    echo "✅ Python protobuf files generated successfully in python_client/rl_env_engine_client/"
    echo "Generated files:"
    echo "  - python_client/rl_env_engine_client/simulation_pb2.py"
    echo "  - python_client/rl_env_engine_client/simulation_pb2_grpc.py"
else
    echo "❌ Failed to generate Python protobuf files"
    echo "Please ensure grpcio-tools is installed: pip install grpcio-tools"
    exit 1
fi

# 生成类型存根文件（用于IDE自动补全和类型检查）
if command -v protoc-gen-mypy &> /dev/null || python3 -c "import mypy_protobuf" 2>/dev/null; then
    echo "Generating Python type stubs (.pyi files)..."
    python3 -m grpc_tools.protoc \
        --mypy_out=python_client/rl_env_engine_client \
        -I proto \
        proto/simulation.proto
    
    if [ $? -eq 0 ]; then
        echo "✅ Type stub files generated successfully:"
        echo "  - python_client/rl_env_engine_client/simulation_pb2.pyi"
        echo "  - python_client/rl_env_engine_client/simulation_pb2_grpc.pyi"
    else
        echo "Warning: Failed to generate type stubs. Install mypy-protobuf: pip install mypy-protobuf"
    fi
else
    echo "❗️ Note: mypy-protobuf not installed. Type stubs not generated."
    echo "      Install it for IDE autocomplete: pip install mypy-protobuf"
fi

# golang grpc部分

# 确保protoc和相关插件已安装
# brew install protobuf
# go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
# go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

# 生成Go代码
protoc --go_out=. --go_opt=paths=source_relative \
    --go-grpc_out=. --go-grpc_opt=paths=source_relative \
    proto/simulation.proto

echo "✅ Protobuf files generated successfully!"
