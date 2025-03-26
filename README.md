# EMB - Extensible Model-Based Agents

A framework for creating and deploying AI agents for various tasks.

## Repository Structure

This repository is organized into the following main components:

### Core Packages

- **emb-core**: Core functionality and base classes for the EMB framework
- **emb-agents**: Agent implementations (Code, Chat, Plan, Research)
- **emb-extensions**: Extensions for various services (GitHub, Slack, Linear, etc.)
- **emb-cli**: Command-line interface tools

### Applications

The `applications/` directory contains various applications built using the EMB framework:

- **codegen_app**: A Modal-based application for code generation
- **pr_review_bot**: PR review bot
- **slack_rag_agent**: Slack RAG agent
- **And more...**

### Shared Utilities

The `shared/` directory contains utilities shared across the framework:

- **logging**: Logging utilities

## Installation

### Installing the Core Framework

```bash
# Install the core framework
pip install -e emb-core/

# Install agents
pip install -e emb-agents/

# Install extensions
pip install -e emb-extensions/

# Install CLI tools
pip install -e emb-cli/
```

### Installing Applications

Each application in the `applications/` directory can be installed separately:

```bash
# Example: Install the codegen_app
cd applications/codegen_app
pip install -e .
```

## Development

For development, you can install all packages with development dependencies:

```bash
pip install -e "emb-core/[dev]"
pip install -e "emb-agents/[dev]"
pip install -e "emb-extensions/[dev]"
pip install -e "emb-cli/[dev]"
```

## Usage

```python
from emb.core import BaseAgent
from emb.agents import CodeAgent, ChatAgent
from emb.extensions.github import GitHubExtension

# Create a code agent
agent = CodeAgent(...)

# Run the agent
result = agent.run("Write a function to calculate fibonacci numbers")
```

## CLI Usage

```bash
# Check the version
emb --version

# Run the CLI
emb
```