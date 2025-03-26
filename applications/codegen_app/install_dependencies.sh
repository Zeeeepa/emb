#!/bin/bash
# Script to install all required dependencies for the codegen_app

# Set up environment variables
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
EMB_ROOT="$(realpath "$SCRIPT_DIR/../..")"
AGENTGEN_DIR="$EMB_ROOT/AgentGen"
CODEGEN_DIR="$EMB_ROOT/codegen"

echo "Installing from directories:"
echo "- AgentGen: $AGENTGEN_DIR"
echo "- Codegen: $CODEGEN_DIR"

# Install AgentGen in development mode
if [ -d "$AGENTGEN_DIR" ]; then
    echo "Installing AgentGen from local directory..."
    cd "$AGENTGEN_DIR" && pip install -e . && cd "$SCRIPT_DIR"
else
    echo "AgentGen directory not found, installing from GitHub..."
    pip install git+https://github.com/Zeeeepa/emb.git#subdirectory=AgentGen
fi

# Install Codegen in development mode
if [ -d "$CODEGEN_DIR" ]; then
    echo "Installing Codegen from local directory..."
    cd "$CODEGEN_DIR" && pip install -e . && cd "$SCRIPT_DIR"
else
    echo "Codegen directory not found, installing from GitHub..."
    pip install git+https://github.com/codegen-sh/codegen-sdk.git@6a0e101718c247c01399c60b7abf301278a41786
fi

# Install other dependencies from requirements.txt
echo "Installing other dependencies..."
pip install -r "$SCRIPT_DIR/requirements.txt"

echo "All dependencies installed successfully!"