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

for proto_file in "$PROTO_DIR"/*.proto; do
    proto_name=$(basename "$proto_file" .proto)
    echo "  Generating Go code for $proto_name.proto..."
    protoc \
        --go_out="$GO_OUT_DIR" \
        --go_opt=paths=source_relative \
        --go-grpc_out="$GO_OUT_DIR" \
        --go-grpc_opt=paths=source_relative \
        -I "$PROTO_DIR" \
        "$proto_file"

    if [ $? -eq 0 ]; then
        echo "  ✅ $proto_name.pb.go generated"
    else
        echo "  ❌ Failed to generate $proto_name"
        exit 1
    fi
done
echo "✅ All Go protobuf files generated successfully!"

# Generate Python code
echo ""
echo "=== Generating Python Protobuf Code ==="

# Check for Python grpcio-tools
if ! python3 -c "import grpc_tools.protoc" &> /dev/null; then
    echo "Installing grpcio-tools..."
    pip install grpcio-tools
fi

for proto_file in "$PROTO_DIR"/*.proto; do
    proto_name=$(basename "$proto_file" .proto)
    echo "  Generating Python code for $proto_name.proto..."
    python3 -m grpc_tools.protoc \
        --python_out="$PYTHON_OUT_DIR" \
        --grpc_python_out="$PYTHON_OUT_DIR" \
        -I "$PROTO_DIR" \
        "$proto_file"

    if [ $? -eq 0 ]; then
        echo "  ✅ ${proto_name}_pb2.py generated"
    else
        echo "  ❌ Failed to generate $proto_name"
        exit 1
    fi
done
echo "✅ All Python protobuf files generated successfully!"

# Generate Python type stubs (optional)
echo ""
echo "=== Generating Python Type Stubs (optional) ==="

if python3 -c "import mypy_protobuf" &> /dev/null; then
    for proto_file in "$PROTO_DIR"/*.proto; do
        python3 -m grpc_tools.protoc \
            --mypy_out="$PYTHON_OUT_DIR" \
            -I "$PROTO_DIR" \
            "$proto_file"
    done
    
    if [ $? -eq 0 ]; then
        echo "✅ Type stub files generated successfully!"
    else
        echo "Warning: Failed to generate type stubs"
    fi
else
    echo "ℹ️  mypy-protobuf not installed. Type stubs not generated."
    echo "   Install with: pip install mypy-protobuf"
fi

echo ""
echo "=== Proto Generation Complete ==="
