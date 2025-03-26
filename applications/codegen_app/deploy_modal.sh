#!/bin/bash
# Script to deploy the codegen_app to Modal with proper Python path setup

# Set up environment variables
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
EMB_ROOT="$(realpath "$SCRIPT_DIR/../..")"
AGENTGEN_DIR="$EMB_ROOT/AgentGen"
CODEGEN_DIR="$EMB_ROOT/codegen"
AGENTGEN_LOWERCASE_DIR="$EMB_ROOT/agentgen"

# Create symbolic link from agentgen to AgentGen if it doesn't exist
if [ ! -e "$AGENTGEN_LOWERCASE_DIR" ]; then
    echo "Creating symbolic link from agentgen to AgentGen..."
    ln -s "$AGENTGEN_DIR" "$AGENTGEN_LOWERCASE_DIR"
    if [ $? -eq 0 ]; then
        echo "Successfully created symbolic link"
    else
        echo "Warning: Failed to create symbolic link, deployment may fail"
    fi
elif [ ! -L "$AGENTGEN_LOWERCASE_DIR" ]; then
    echo "Warning: $AGENTGEN_LOWERCASE_DIR exists but is not a symbolic link"
fi

# Set up Python path to include both codegen and agentgen
export PYTHONPATH="$PYTHONPATH:$AGENTGEN_DIR:$CODEGEN_DIR:$EMB_ROOT"

echo "Setting up Python path:"
echo "- AgentGen: $AGENTGEN_DIR"
echo "- Codegen: $CODEGEN_DIR"
echo "- EMB Root: $EMB_ROOT"

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