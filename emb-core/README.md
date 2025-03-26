# EMB Core

Core functionality for the EMB framework.

## Installation

```bash
pip install -e .
```

## Usage

```python
from emb.core import BaseAgent, Config

# Create a configuration
config = Config(model_name="gpt-4")

# Use the base agent
agent = BaseAgent(config)
```