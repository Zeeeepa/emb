#!/bin/bash

# AgentGen Setup Script
# This script installs the AgentGen package and its dependencies

set -e  # Exit on error

# Print colored messages
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== AgentGen Setup ===${NC}"

# Check if running as root for system package installation
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Note: Some system dependencies may require sudo privileges.${NC}"
    echo -e "${YELLOW}You may be prompted for your password.${NC}"
fi

# Install system dependencies
echo -e "${YELLOW}Checking and installing system dependencies...${NC}"

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    OS=$(uname -s)
fi

case $OS in
    ubuntu|debian|linuxmint)
        echo -e "${YELLOW}Detected Debian/Ubuntu-based system.${NC}"
        echo -e "${YELLOW}Updating package lists...${NC}"
        sudo apt-get update -qq
        
        echo -e "${YELLOW}Installing required packages...${NC}"
        sudo apt-get install -y -qq python3 python3-pip python3-venv python3.12-venv build-essential libssl-dev libffi-dev python3-dev git
        ;;
    fedora|centos|rhel)
        echo -e "${YELLOW}Detected Fedora/CentOS/RHEL system.${NC}"
        sudo dnf update -y -q
        sudo dnf install -y python3 python3-pip python3-devel gcc openssl-devel libffi-devel git
        ;;
    darwin)
        echo -e "${YELLOW}Detected macOS.${NC}"
        if ! command -v brew &> /dev/null; then
            echo -e "${YELLOW}Homebrew not found. Installing Homebrew...${NC}"
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        brew update
        brew install python3 openssl git
        ;;
    *)
        echo -e "${YELLOW}Unsupported OS. You may need to install dependencies manually.${NC}"
        ;;
esac

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

# Create missing __init__.py files
echo -e "${YELLOW}Creating missing __init__.py files...${NC}"

# Function to create __init__.py if it doesn't exist
create_init_if_missing() {
    if [ ! -f "$1/__init__.py" ]; then
        echo -e "${YELLOW}Creating $1/__init__.py${NC}"
        mkdir -p "$1"
        echo "# Auto-generated __init__.py file" > "$1/__init__.py"
    fi
}

# Create __init__.py files in all required directories
create_init_if_missing "agents"
create_init_if_missing "cli"
create_init_if_missing "cli/commands"
create_init_if_missing "cli/commands/agent"
create_init_if_missing "cli/mcp"
create_init_if_missing "cli/mcp/agent"
create_init_if_missing "cli/mcp/resources"
create_init_if_missing "configs"
create_init_if_missing "configs/models"
create_init_if_missing "extensions"
create_init_if_missing "extensions/clients"
create_init_if_missing "extensions/github"
create_init_if_missing "extensions/github/types"
create_init_if_missing "extensions/github/types/events"
create_init_if_missing "extensions/langchain"
create_init_if_missing "extensions/linear"
create_init_if_missing "extensions/slack"
create_init_if_missing "extensions/tools"
create_init_if_missing "tests"

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

# Create README.md if it doesn't exist
if [ ! -f "README.md" ]; then
    echo -e "${YELLOW}Creating README.md...${NC}"
    cat > README.md << EOF
# AgentGen

A framework for creating code agents.

## Installation

```bash
# Install with pip
pip install -e .

# Or install with uv
uv pip install -e .
```

## Usage

```bash
# Show version
agentgen --version

# Show help
agentgen --help
```
EOF
    echo -e "${GREEN}README.md created.${NC}"
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
    if python -c "import agentgen; print(f'AgentGen version: {agentgen.__version__}')" 2>/dev/null; then
        echo -e "${GREEN}Package import successful.${NC}"
    else
        echo -e "${YELLOW}Warning: Package installed but import verification failed.${NC}"
        echo -e "${YELLOW}You may need to restart your terminal or Python interpreter.${NC}"
    fi
    
    if command -v agentgen &> /dev/null; then
        echo -e "${GREEN}AgentGen command is available.${NC}"
        echo -e "${YELLOW}Version information:${NC}"
        agentgen --version
    else
        echo -e "${YELLOW}Warning: 'agentgen' command not found in PATH.${NC}"
        echo -e "${YELLOW}You may need to restart your terminal or add the bin directory to your PATH.${NC}"
    fi
    
    echo -e "${GREEN}=== Setup Complete ===${NC}"
    echo -e "${YELLOW}You can now use AgentGen by running 'agentgen' in your terminal.${NC}"
    echo -e "${YELLOW}You can also import the package in Python with 'import agentgen'.${NC}"
else
    echo -e "${RED}Installation failed.${NC}"
    exit 1
fi