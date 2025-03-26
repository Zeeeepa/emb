#!/bin/bash
# Script to deploy the codegen_app locally for testing

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

# Deploy with Modal
cd "$SCRIPT_DIR"
modal deploy app.py

echo "Deployment completed!"