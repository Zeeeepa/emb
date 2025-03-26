#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
  echo -e "${BLUE}[INTEGRATION]${NC} $1"
}

print_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Check if codegen directory is provided
if [ $# -eq 0 ]; then
  print_error "Please provide the path to the codegen repository."
  echo "Usage: $0 /path/to/codegen"
  exit 1
fi

CODEGEN_DIR=$1
CURRENT_DIR=$(pwd)

# Check if the provided directory exists
if [ ! -d "$CODEGEN_DIR" ]; then
  print_error "The directory $CODEGEN_DIR does not exist."
  exit 1
fi

# Check if the provided directory is a codegen repository
if [ ! -f "$CODEGEN_DIR/pyproject.toml" ] || ! grep -q "codegen" "$CODEGEN_DIR/pyproject.toml"; then
  print_warning "The directory $CODEGEN_DIR does not appear to be a codegen repository."
  read -p "Continue anyway? (y/n) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

# Check if we're in the AgentGen directory
if [ ! -f "pyproject.toml" ] || ! grep -q "agentgen" "pyproject.toml"; then
  print_error "Please run this script from the AgentGen directory."
  exit 1
fi

print_message "Starting integration of AgentGen with Codegen..."

# Create the agentgen directory in codegen/src/codegen
AGENTGEN_DIR="$CODEGEN_DIR/src/codegen/agentgen"
print_message "Creating directory: $AGENTGEN_DIR"
mkdir -p "$AGENTGEN_DIR"

# Copy all files from AgentGen to the new directory
print_message "Copying AgentGen files to $AGENTGEN_DIR"
cp -r ./* "$AGENTGEN_DIR/"

# Create __init__.py file
print_message "Creating __init__.py file"
cat > "$AGENTGEN_DIR/__init__.py" << 'EOF'
"""
AgentGen - AI Agent Framework for Codegen

This module provides AI agents for code generation, analysis, and chat interactions.
"""

from .agents.code_agent import CodeAgent
from .agents.chat_agent import ChatAgent
from .agents.factory import (
    create_codebase_agent,
    create_chat_agent,
    create_codebase_inspector_agent,
    create_agent_with_tools
)

__all__ = [
    'CodeAgent',
    'ChatAgent',
    'create_codebase_agent',
    'create_chat_agent',
    'create_codebase_inspector_agent',
    'create_agent_with_tools',
]
EOF

# Update the codegen pyproject.toml to include agentgen as a dependency
print_message "Updating codegen's pyproject.toml"
if ! grep -q "agentgen" "$CODEGEN_DIR/pyproject.toml"; then
  # Find the dependencies section and add agentgen
  sed -i '/dependencies = \[/a \ \ \ \ "agentgen",  # Integrated AgentGen module' "$CODEGEN_DIR/pyproject.toml"
fi

# Install codegen with the integrated agentgen
print_message "Installing codegen with integrated agentgen"
cd "$CODEGEN_DIR"
pip install -e .

# Return to the original directory
cd "$CURRENT_DIR"

print_success "Integration complete!"
print_message "You can now import AgentGen in your Codegen applications:"
echo -e "${BLUE}from codegen.agentgen import CodeAgent, ChatAgent, create_codebase_agent${NC}"

# Provide instructions for updating existing code
print_message "To update existing code that imports from agentgen, change:"
echo -e "${RED}from agentgen import ...${NC}"
echo -e "to:"
echo -e "${GREEN}from codegen.agentgen import ...${NC}"

print_message "For more details, see the INTEGRATION.md file."