#!/bin/bash
# Script to deploy the codegen_app to Modal with proper Python path setup

# Set up environment variables
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
EMB_ROOT="$(realpath "$SCRIPT_DIR/../..")"
AGENTGEN_DIR="$EMB_ROOT/AgentGen"
CODEGEN_DIR="$EMB_ROOT/codegen"

# Create symbolic link from agentgen to AgentGen
bash "$SCRIPT_DIR/fix_agentgen_symlink.sh"

# Set up Python path to include both codegen and agentgen
export PYTHONPATH="$PYTHONPATH:$EMB_ROOT:$AGENTGEN_DIR:$CODEGEN_DIR"

echo "Setting up Python path:"
echo "- EMB Root: $EMB_ROOT"
echo "- AgentGen: $AGENTGEN_DIR"
echo "- Codegen: $CODEGEN_DIR"

# Make sure agentgen is importable
if python -c "import agentgen" &> /dev/null; then
    echo "✅ agentgen package is importable"
else
    echo "❌ agentgen package is not importable"
    echo "Installing agentgen in development mode..."
    cd "$AGENTGEN_DIR" && pip install -e . && cd "$SCRIPT_DIR"
fi

# Make sure codegen is importable
if python -c "import codegen" &> /dev/null; then
    echo "✅ codegen package is importable"
else
    echo "❌ codegen package is not importable"
    echo "Installing codegen in development mode..."
    cd "$CODEGEN_DIR" && pip install -e . && cd "$SCRIPT_DIR"
fi

# Deploy with Modal
cd "$SCRIPT_DIR"
modal deploy app.py

echo "Deployment completed!"