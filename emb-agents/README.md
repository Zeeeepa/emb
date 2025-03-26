# EMB Agents

Agent implementations for the EMB framework.

## Installation

```bash
pip install -e .
```

## Usage

```python
from emb.agents import CodeAgent, ChatAgent
from emb.core import Config

# Create a configuration
config = Config(model_name="gpt-4")

# Create a code agent
code_agent = CodeAgent(config)

# Create a chat agent
chat_agent = ChatAgent(config)
```