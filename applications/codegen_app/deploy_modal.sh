#!/bin/bash
# Script to deploy the codegen_app to Modal with proper Python path setup

# Set up environment variables
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
EMB_ROOT="$(realpath "$SCRIPT_DIR/../..")"
AGENTGEN_DIR="$EMB_ROOT/AgentGen"
CODEGEN_DIR="$EMB_ROOT/codegen"


# Print Python path for debugging
echo "Python path: $PYTHONPATH"

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