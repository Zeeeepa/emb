#!/bin/bash
# Script to deploy the codegen_app locally for testing

# Set up environment variables
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
EMB_ROOT="$(realpath "$SCRIPT_DIR/../..")"
AGENTGEN_DIR="$EMB_ROOT/AgentGen"
CODEGEN_DIR="$EMB_ROOT/codegen"

# Set up Python path to include both codegen and agentgen
export PYTHONPATH="$PYTHONPATH:$AGENTGEN_DIR:$CODEGEN_DIR"

echo "Setting up Python path:"
echo "- AgentGen: $AGENTGEN_DIR"
echo "- Codegen: $CODEGEN_DIR"

# Deploy with Modal
cd "$SCRIPT_DIR"
modal deploy app.py

echo "Deployment completed!"