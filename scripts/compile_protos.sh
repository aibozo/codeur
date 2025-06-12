#!/bin/bash
# Script to compile protobuf files to Python

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "Compiling Protocol Buffer definitions..."

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Source and destination directories
PROTO_DIR="$PROJECT_ROOT/src/proto"
PYTHON_OUT="$PROJECT_ROOT/src/proto_gen"

# Create output directory if it doesn't exist
mkdir -p "$PYTHON_OUT"

# Check if protoc is installed
if ! command -v protoc &> /dev/null; then
    echo -e "${RED}Error: protoc (Protocol Buffer compiler) is not installed.${NC}"
    echo "Please install it:"
    echo "  - macOS: brew install protobuf"
    echo "  - Ubuntu/Debian: sudo apt-get install protobuf-compiler"
    echo "  - Or download from: https://github.com/protocolbuffers/protobuf/releases"
    exit 1
fi

# Check if Python protobuf is installed
if ! python3 -c "import google.protobuf" 2>/dev/null; then
    echo -e "${RED}Error: Python protobuf package is not installed.${NC}"
    echo "Please install it: pip install protobuf"
    exit 1
fi

# Compile proto files
echo "Compiling messages.proto..."
protoc \
    --proto_path="$PROTO_DIR" \
    --python_out="$PYTHON_OUT" \
    "$PROTO_DIR/messages.proto"

# Create __init__.py file
touch "$PYTHON_OUT/__init__.py"

echo -e "${GREEN}✓ Protocol Buffers compiled successfully!${NC}"
echo "Generated Python files in: $PYTHON_OUT"

# Show generated files
echo -e "\nGenerated files:"
find "$PYTHON_OUT" -name "*.py" -type f | while read -r file; do
    echo "  - ${file#$PROJECT_ROOT/}"
done