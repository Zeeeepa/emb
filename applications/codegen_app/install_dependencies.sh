#!/bin/bash
# Script to install all dependencies for the codegen_app

# Set up environment variables
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
EMB_ROOT="$(realpath "$SCRIPT_DIR/../..")"
AGENTGEN_DIR="$EMB_ROOT/AgentGen"
CODEGEN_DIR="$EMB_ROOT/codegen"

# Create symbolic link from agentgen to AgentGen
bash "$SCRIPT_DIR/fix_agentgen_symlink.sh"

# Install dependencies from requirements.txt
echo "Installing dependencies from requirements.txt..."
pip install -r "$SCRIPT_DIR/requirements.txt"

# Install agentgen in development mode if needed
if [ -d "$AGENTGEN_DIR" ]; then
    echo "Installing agentgen in development mode..."
    cd "$AGENTGEN_DIR" && pip install -e . && cd "$SCRIPT_DIR"
fi

# Install codegen in development mode if needed
if [ -d "$CODEGEN_DIR" ]; then
    echo "Installing codegen in development mode..."
    cd "$CODEGEN_DIR" && pip install -e . && cd "$SCRIPT_DIR"
fi

echo "All dependencies installed successfully!"