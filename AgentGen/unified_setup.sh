#!/bin/bash
# Make this script executable with: chmod +x unified_setup.sh

# Unified Setup Script for Codegen and AgentGen
# This script installs both codegen and agentgen packages in development mode

set -e  # Exit on error

# Print colored messages
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Unified Codegen & AgentGen Setup ===${NC}"

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
        
        echo -e "${YELLOW}Upgrading packages...${NC}"
        sudo apt-get upgrade -y -qq
        
        echo -e "${YELLOW}Installing required packages...${NC}"
        sudo apt-get install -y -qq python3 python3-pip python3-venv python3.12-venv build-essential libssl-dev libffi-dev python3-dev git curl
        ;;
    fedora|centos|rhel)
        echo -e "${YELLOW}Detected Fedora/CentOS/RHEL system.${NC}"
        sudo dnf update -y -q
        sudo dnf install -y python3 python3-pip python3-devel gcc openssl-devel libffi-devel git curl
        ;;
    darwin)
        echo -e "${YELLOW}Detected macOS.${NC}"
        if ! command -v brew &> /dev/null; then
            echo -e "${YELLOW}Homebrew not found. Installing Homebrew...${NC}"
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        brew update
        brew install python3 openssl git curl
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

# Install uv if not already installed
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}Installing uv package manager...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Add uv to PATH for the current session
    export PATH="$HOME/.cargo/bin:$PATH"
    export PATH="$HOME/.uv/bin:$PATH"
    
    # Source shell integration if available
    if [ -f "$HOME/.uv/env" ]; then
        . "$HOME/.uv/env"
    fi
    
    if ! command -v uv &> /dev/null; then
        echo -e "${YELLOW}uv installation may require a terminal restart. Continuing with pip...${NC}"
    else
        echo -e "${GREEN}uv installed successfully!${NC}"
    fi
fi

# Create or activate virtual environment automatically
VENV_DIR=".venv"
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}No active virtual environment detected. Creating one automatically...${NC}"
    
    # Check if venv module is available
    if ! python3 -c "import venv" &> /dev/null; then
        echo -e "${RED}Error: Python venv module is not available. Please install it first.${NC}"
        exit 1
    fi
    
    # Create virtual environment
    python3 -m venv $VENV_DIR
    
    # Activate virtual environment
    echo -e "${GREEN}Activating virtual environment...${NC}"
    source $VENV_DIR/bin/activate
    
    echo -e "${GREEN}Virtual environment created and activated.${NC}"
else
    echo -e "${GREEN}Using active virtual environment: $VIRTUAL_ENV${NC}"
fi

# Create missing __init__.py files for AgentGen
echo -e "${YELLOW}Creating missing __init__.py files for AgentGen...${NC}"

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

# Create README.md if it doesn't exist
if [ ! -f "README.md" ]; then
    echo -e "${YELLOW}Creating README.md...${NC}"
    cat > README.md << EOF
# AgentGen

A framework for creating code agents.

## Installation

```bash
# Install with the unified setup script
./unified_setup.sh

# Or install manually
pip install -e .
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

# Update pyproject.toml
echo -e "${YELLOW}Updating pyproject.toml...${NC}"
cat > pyproject.toml << EOF
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "agentgen"
version = "0.1.0"
authors = [
    {name = "AgentGen Team", email = "info@example.com"},
]
description = "A framework for creating code agents"
readme = "README.md"
requires-python = ">=3.9"
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
]
dependencies = [
    "langchain>=0.0.267",
    "langgraph>=0.0.10",
    "openai>=0.27.0",
    "anthropic>=0.3.0",
    "pydantic>=2.0.0",
    "typer>=0.9.0",
    "rich>=13.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "black>=23.0.0",
    "isort>=5.0.0",
    "mypy>=1.0.0",
]

[project.scripts]
agentgen = "cli.main:app"

[tool.setuptools]
packages = ["agents", "cli", "configs", "extensions", "tests"]
package-dir = {"" = "."}

[tool.black]
line-length = 88
target-version = ["py39"]

[tool.isort]
profile = "black"
line_length = 88

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
EOF

# Update setup.py
echo -e "${YELLOW}Updating setup.py...${NC}"
cat > setup.py << EOF
from setuptools import setup, find_packages

setup(
    name="agentgen",
    packages=find_packages(include=["agents", "agents.*", "cli", "cli.*", "configs", "configs.*",
                                    "extensions", "extensions.*", "tests", "tests.*"]),
    package_dir={"": "."},
    entry_points={
        "console_scripts": [
            "agentgen=cli.main:app",
        ],
    },
)
EOF

# Create main.py in cli directory
echo -e "${YELLOW}Creating cli/main.py...${NC}"
mkdir -p cli
cat > cli/main.py << EOF
#!/usr/bin/env python3
import typer
import importlib.metadata

app = typer.Typer(help="AgentGen CLI")

@app.callback()
def callback():
    """
    AgentGen CLI
    """
    pass

@app.command()
def version():
    """Show the version of AgentGen"""
    try:
        version = importlib.metadata.version("agentgen")
        typer.echo(f"agentgen version {version}")
    except importlib.metadata.PackageNotFoundError:
        typer.echo("agentgen version unknown (package not installed)")

if __name__ == "__main__":
    app()
EOF

# Clone and install codegen if not already installed
CODEGEN_DIR="$HOME/LIBS/codegen"
if [ ! -d "$CODEGEN_DIR" ]; then
    echo -e "${YELLOW}Cloning codegen repository...${NC}"
    mkdir -p "$HOME/LIBS"
    git clone https://github.com/Zeeeepa/codegen.git "$CODEGEN_DIR"
    echo -e "${GREEN}Codegen repository cloned to $CODEGEN_DIR${NC}"
else
    echo -e "${YELLOW}Codegen repository already exists at $CODEGEN_DIR${NC}"
    echo -e "${YELLOW}Updating codegen repository...${NC}"
    cd "$CODEGEN_DIR"
    git pull
    cd - > /dev/null
fi

# Install codegen
echo -e "${CYAN}=== Installing Codegen ===${NC}"
cd "$CODEGEN_DIR"

if command -v uv &> /dev/null; then
    echo -e "${YELLOW}Installing codegen with uv...${NC}"
    uv pip install -e . --system
    CODEGEN_INSTALL_STATUS=$?
    
    if [ $CODEGEN_INSTALL_STATUS -ne 0 ]; then
        echo -e "${RED}Installation with uv failed. Falling back to pip...${NC}"
        pip install -e .
        CODEGEN_INSTALL_STATUS=$?
    fi
else
    echo -e "${YELLOW}Installing codegen with pip...${NC}"
    pip install -e .
    CODEGEN_INSTALL_STATUS=$?
fi

if [ $CODEGEN_INSTALL_STATUS -ne 0 ]; then
    echo -e "${RED}Codegen installation failed. Please check the error messages above.${NC}"
    exit 1
fi

# Return to AgentGen directory
cd - > /dev/null

# Install AgentGen
echo -e "${CYAN}=== Installing AgentGen ===${NC}"

if command -v uv &> /dev/null; then
    echo -e "${YELLOW}Installing AgentGen with uv...${NC}"
    uv pip install -e . --system
    AGENTGEN_INSTALL_STATUS=$?
    
    if [ $AGENTGEN_INSTALL_STATUS -ne 0 ]; then
        echo -e "${RED}Installation with uv failed. Falling back to pip...${NC}"
        pip install -e .
        AGENTGEN_INSTALL_STATUS=$?
    fi
else
    echo -e "${YELLOW}Installing AgentGen with pip...${NC}"
    pip install -e .
    AGENTGEN_INSTALL_STATUS=$?
fi

if [ $AGENTGEN_INSTALL_STATUS -ne 0 ]; then
    echo -e "${RED}AgentGen installation failed. Please check the error messages above.${NC}"
    exit 1
fi

# Check if installations were successful
echo -e "${CYAN}=== Verifying Installation ===${NC}"

# Check codegen
if command -v codegen &> /dev/null; then
    echo -e "${GREEN}Codegen command is available.${NC}"
    echo -e "${YELLOW}Codegen version:${NC}"
    codegen --version
else
    echo -e "${RED}Warning: 'codegen' command not found in PATH.${NC}"
    echo -e "${YELLOW}You may need to restart your terminal or add the bin directory to your PATH.${NC}"
fi

# Check agentgen
if command -v agentgen &> /dev/null; then
    echo -e "${GREEN}AgentGen command is available.${NC}"
    echo -e "${YELLOW}AgentGen version:${NC}"
    agentgen --version
else
    echo -e "${RED}Warning: 'agentgen' command not found in PATH.${NC}"
    echo -e "${YELLOW}You may need to restart your terminal or add the bin directory to your PATH.${NC}"
fi

# Try importing the packages
echo -e "${YELLOW}Testing imports...${NC}"
if python3 -c "import codegen; print(f'Codegen imported successfully')" 2>/dev/null; then
    echo -e "${GREEN}Codegen package import successful.${NC}"
else
    echo -e "${RED}Warning: Codegen package import failed.${NC}"
    echo -e "${YELLOW}You may need to restart your terminal or Python interpreter.${NC}"
fi

if python3 -c "import agentgen; print(f'AgentGen imported successfully')" 2>/dev/null; then
    echo -e "${GREEN}AgentGen package import successful.${NC}"
else
    echo -e "${RED}Warning: AgentGen package import failed.${NC}"
    echo -e "${YELLOW}You may need to restart your terminal or Python interpreter.${NC}"
fi

echo -e "${GREEN}=== Setup Complete ===${NC}"
echo -e "${YELLOW}You can now use Codegen and AgentGen in your projects.${NC}"
echo -e "${YELLOW}Run 'codegen --help' or 'agentgen --help' to see available commands.${NC}"
echo -e "${BLUE}Happy coding!${NC}"