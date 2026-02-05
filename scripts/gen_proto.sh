#!/bin/bash
# Generate protobuf code for Go and Python
# Usage: ./scripts/gen_proto.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

PROTO_DIR="$ROOT_DIR/api/proto/v1"
GO_OUT_DIR="$ROOT_DIR/go/pkg/api/v1"
PYTHON_OUT_DIR="$ROOT_DIR/python/src/rl_env_engine/generated"

echo "=== Generating Protobuf Code ==="
echo "Proto source: $PROTO_DIR"
echo "Go output: $GO_OUT_DIR"
echo "Python output: $PYTHON_OUT_DIR"
echo ""

# Create output directories
mkdir -p "$GO_OUT_DIR"
mkdir -p "$PYTHON_OUT_DIR"

# Check for required tools
check_tool() {
    if ! command -v "$1" &> /dev/null; then
        echo "Error: $1 is not installed"
        echo "  Install with: $2"
        exit 1
    fi
}

echo "Checking required tools..."
check_tool "protoc" "brew install protobuf (macOS) or apt install protobuf-compiler (Linux)"

# Generate Go code
echo ""
echo "=== Generating Go Protobuf Code ==="

# Check for Go protoc plugins
if ! command -v protoc-gen-go &> /dev/null; then
    echo "Installing protoc-gen-go..."
    go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
fi

if ! command -v protoc-gen-go-grpc &> /dev/null; then
    echo "Installing protoc-gen-go-grpc..."
    go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
fi

# Ensure Go bin is in PATH
export PATH="$PATH:$(go env GOPATH)/bin"

protoc \
    --go_out="$GO_OUT_DIR" \
    --go_opt=paths=source_relative \
    --go-grpc_out="$GO_OUT_DIR" \
    --go-grpc_opt=paths=source_relative \
    -I "$PROTO_DIR" \
    "$PROTO_DIR/simulation.proto"

if [ $? -eq 0 ]; then
    echo "✅ Go protobuf files generated successfully!"
    echo "   $GO_OUT_DIR/simulation.pb.go"
    echo "   $GO_OUT_DIR/simulation_grpc.pb.go"
else
    echo "❌ Failed to generate Go protobuf files"
    exit 1
fi

# Generate Python code
echo ""
echo "=== Generating Python Protobuf Code ==="

# Check for Python grpcio-tools
if ! python3 -c "import grpc_tools.protoc" &> /dev/null; then
    echo "Installing grpcio-tools..."
    pip install grpcio-tools
fi

python3 -m grpc_tools.protoc \
    --python_out="$PYTHON_OUT_DIR" \
    --grpc_python_out="$PYTHON_OUT_DIR" \
    -I "$PROTO_DIR" \
    "$PROTO_DIR/simulation.proto"

if [ $? -eq 0 ]; then
    echo "✅ Python protobuf files generated successfully!"
    echo "   $PYTHON_OUT_DIR/simulation_pb2.py"
    echo "   $PYTHON_OUT_DIR/simulation_pb2_grpc.py"
else
    echo "❌ Failed to generate Python protobuf files"
    exit 1
fi

# Generate Python type stubs (optional)
echo ""
echo "=== Generating Python Type Stubs (optional) ==="

if python3 -c "import mypy_protobuf" &> /dev/null; then
    python3 -m grpc_tools.protoc \
        --mypy_out="$PYTHON_OUT_DIR" \
        -I "$PROTO_DIR" \
        "$PROTO_DIR/simulation.proto"
    
    if [ $? -eq 0 ]; then
        echo "✅ Type stub files generated successfully!"
        echo "   $PYTHON_OUT_DIR/simulation_pb2.pyi"
    else
        echo "Warning: Failed to generate type stubs"
    fi
else
    echo "ℹ️  mypy-protobuf not installed. Type stubs not generated."
    echo "   Install with: pip install mypy-protobuf"
fi

echo ""
echo "=== Proto Generation Complete ==="
