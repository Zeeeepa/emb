#!/bin/bash

# AgentGen Setup Script
# This script installs the AgentGen package and its dependencies

set -e  # Exit on error

# Print colored messages
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== AgentGen Setup ===${NC}"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed. Please install Python 3.9 or higher.${NC}"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    echo -e "${RED}Error: Python 3.9 or higher is required. Found Python $PYTHON_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}Using Python $PYTHON_VERSION${NC}"

# Create missing __init__.py files if needed
echo -e "${YELLOW}Ensuring all directories have __init__.py files...${NC}"

# Create __init__.py in github/types/events
if [ ! -f "extensions/github/types/events/__init__.py" ]; then
    echo "Creating extensions/github/types/events/__init__.py"
    mkdir -p extensions/github/types/events
    echo '"""GitHub event types."""' > extensions/github/types/events/__init__.py
fi

# Check for virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}No active virtual environment detected.${NC}"
    
    # Ask if user wants to create a virtual environment
    read -p "Do you want to create a virtual environment? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}Creating virtual environment...${NC}"
        
        # Check if venv module is available
        if ! python3 -c "import venv" &> /dev/null; then
            echo -e "${RED}Error: Python venv module is not available. Please install it first.${NC}"
            exit 1
        fi
        
        # Create virtual environment
        python3 -m venv .venv
        
        # Activate virtual environment
        echo -e "${GREEN}Activating virtual environment...${NC}"
        source .venv/bin/activate
        
        echo -e "${GREEN}Virtual environment created and activated.${NC}"
    else
        echo -e "${YELLOW}Proceeding without virtual environment...${NC}"
    fi
else
    echo -e "${GREEN}Using active virtual environment: $VIRTUAL_ENV${NC}"
fi

# Check if uv is installed
if command -v uv &> /dev/null; then
    echo -e "${GREEN}Using uv for package installation...${NC}"
    
    # Install with uv
    echo -e "${YELLOW}Installing AgentGen with uv...${NC}"
    uv pip install -e .
    
    INSTALL_STATUS=$?
    if [ $INSTALL_STATUS -ne 0 ]; then
        echo -e "${RED}Installation with uv failed. Falling back to pip...${NC}"
        pip install -e .
    fi
else
    echo -e "${YELLOW}uv not found, using pip for installation...${NC}"
    
    # Install with pip
    echo -e "${YELLOW}Installing AgentGen with pip...${NC}"
    pip install -e .
fi

# Check if installation was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}AgentGen has been successfully installed!${NC}"
    
    # Test the installation
    echo -e "${YELLOW}Testing installation...${NC}"
    if command -v agentgen &> /dev/null; then
        echo -e "${GREEN}AgentGen command is available.${NC}"
        echo -e "${YELLOW}Version information:${NC}"
        agentgen --version
    else
        echo -e "${RED}Warning: 'agentgen' command not found in PATH.${NC}"
        echo -e "${YELLOW}You may need to restart your terminal or add the bin directory to your PATH.${NC}"
    fi
    
    echo -e "${GREEN}=== Setup Complete ===${NC}"
    echo -e "${YELLOW}You can now use AgentGen by running 'agentgen' in your terminal.${NC}"
else
    echo -e "${RED}Installation failed.${NC}"
    exit 1
fi