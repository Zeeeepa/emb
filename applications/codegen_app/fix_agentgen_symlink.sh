#!/bin/bash
# Script to create a symbolic link from agentgen to AgentGen

# Set up environment variables
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
EMB_ROOT="$(realpath "$SCRIPT_DIR/../..")"
AGENTGEN_DIR="$EMB_ROOT/AgentGen"
AGENTGEN_LOWERCASE_DIR="$EMB_ROOT/agentgen"

# Check if AgentGen directory exists
if [ ! -d "$AGENTGEN_DIR" ]; then
    echo "❌ AgentGen directory not found at $AGENTGEN_DIR"
    exit 1
fi

# Create symbolic link if it doesn't exist
if [ ! -L "$AGENTGEN_LOWERCASE_DIR" ]; then
    echo "Creating symbolic link from agentgen to AgentGen..."
    ln -s "$AGENTGEN_DIR" "$AGENTGEN_LOWERCASE_DIR"
    echo "✅ Symbolic link created"
else
    echo "✅ Symbolic link already exists"
fi

# Verify the link works
if [ -L "$AGENTGEN_LOWERCASE_DIR" ] && [ -d "$AGENTGEN_LOWERCASE_DIR" ]; then
    echo "✅ Symbolic link is valid"
else
    echo "❌ Symbolic link is invalid"
    exit 1
fi

echo "Done!"