#!/bin/bash

# 生成Python gRPC客户端代码
# 确保安装了必要的包：pip install grpcio-tools

echo "Generating Python protobuf files..."

# 切换到项目根目录
cd "$(dirname "$0")"

# 生成Python protobuf代码
python3 -m grpc_tools.protoc \
    --python_out=python_client \
    --grpc_python_out=python_client \
    -I proto \
    proto/simulation.proto

if [ $? -eq 0 ]; then
    echo "Python protobuf files generated successfully in python_client/"
    echo "Generated files:"
    echo "  - python_client/simulation_pb2.py"
    echo "  - python_client/simulation_pb2_grpc.py"
else
    echo "Failed to generate Python protobuf files"
    echo "Please ensure grpcio-tools is installed: pip install grpcio-tools"
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

echo "Protobuf files generated successfully!"
