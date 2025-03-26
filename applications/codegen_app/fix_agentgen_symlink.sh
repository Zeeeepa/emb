#!/bin/bash
# Script to create a symbolic link from agentgen to AgentGen

# Set up environment variables
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
EMB_ROOT="$(realpath "$SCRIPT_DIR/../..")"
AGENTGEN_DIR="$EMB_ROOT/AgentGen"
AGENTGEN_LOWERCASE_DIR="$EMB_ROOT/agentgen"

echo "Creating symbolic link from agentgen to AgentGen..."

# Check if AgentGen directory exists
if [ ! -d "$AGENTGEN_DIR" ]; then
    echo "Error: AgentGen directory not found at $AGENTGEN_DIR"
    exit 1
fi

# Check if lowercase agentgen already exists
if [ -e "$AGENTGEN_LOWERCASE_DIR" ]; then
    echo "Warning: agentgen already exists at $AGENTGEN_LOWERCASE_DIR"
    
    # If it's a symlink, we're good
    if [ -L "$AGENTGEN_LOWERCASE_DIR" ]; then
        echo "It's already a symbolic link, no action needed."
        exit 0
    else
        echo "Error: agentgen exists but is not a symbolic link. Please remove it first."
        exit 1
    fi
fi

# Create the symbolic link
ln -s "$AGENTGEN_DIR" "$AGENTGEN_LOWERCASE_DIR"

if [ $? -eq 0 ]; then
    echo "Successfully created symbolic link from $AGENTGEN_LOWERCASE_DIR to $AGENTGEN_DIR"
else
    echo "Error: Failed to create symbolic link"
    exit 1
fi

echo "Done!"