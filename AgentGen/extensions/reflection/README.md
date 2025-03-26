# AgentGen Reflection Module

This module provides enhanced reflection capabilities for AgentGen agents, allowing them to self-critique and improve their responses through a reflection process.

## Overview

The reflection module is inspired by LangGraph's reflection framework and provides a way to create agents that can:

1. Generate initial responses to user queries
2. Critique their own responses based on various criteria
3. Improve their responses based on the critique
4. Repeat this process until a satisfactory response is generated

## Key Components

- `MessagesWithSteps`: State class for reflection graphs with remaining steps tracking
- `create_reflection_graph`: Function to create a reflection-enhanced graph
- `create_llm_reflection_node`: Function to create a general-purpose reflection node
- `create_code_reflection_node`: Function to create a code-specific reflection node
- `create_reflection_enhanced_agent`: High-level function to create a reflection-enhanced agent

## Usage

### Basic Usage

```python
from codegen import Codebase
from agentgen.extensions.langchain.agent import create_codebase_agent
from agentgen.extensions.reflection import create_reflection_enhanced_agent

# Create a codebase
codebase = Codebase.from_repo("owner/repo")

# Create a base agent graph
base_agent_graph = create_codebase_agent(
    codebase=codebase,
    model_provider="anthropic",
    model_name="claude-3-5-sonnet-latest",
    memory=True,
)

# Create a reflection-enhanced agent
reflection_agent = create_reflection_enhanced_agent(
    agent_graph=base_agent_graph,
    reflection_type="general",  # or "code" for code-specific reflection
    model_provider="anthropic",
    model_name="claude-3-5-sonnet-latest",
    max_reflection_iterations=3,
)

# Run the agent
result = reflection_agent.invoke({"messages": [], "query": "Your query here"})

# Get the final answer
final_answer = result["final_answer"]
```

### Advanced Usage: Custom Reflection Nodes

You can create custom reflection nodes for specific use cases:

```python
from agentgen.extensions.reflection.reflection_graph import (
    MessagesWithSteps,
    create_reflection_graph,
)
from langgraph.graph import END, START, StateGraph

# Create a custom reflection node
def custom_reflection_node(state):
    # Your custom reflection logic here
    # ...
    return {"messages": new_messages, "remaining_steps": remaining_steps}

# Create a reflection graph with your custom node
reflection_graph = StateGraph(MessagesWithSteps)
reflection_graph.add_node("reflect", custom_reflection_node)
reflection_graph.add_edge(START, "reflect")
reflection_graph.add_edge("reflect", END)
compiled_reflection = reflection_graph.compile()

# Create the reflection-enhanced graph
reflection_agent = create_reflection_graph(
    agent_graph=base_agent_graph,
    reflection_graph=compiled_reflection,
    max_reflection_iterations=3,
).compile()
```

## Example Applications

The module includes example applications that demonstrate how to use the reflection capabilities:

1. `applications/reflection_agent/run.py`: Basic reflection agent
2. `applications/reflection_agent/code_reflection.py`: Code-specific reflection agent with automated evaluation

### Running the Examples

```bash
# Run the basic reflection agent
python -m applications.reflection_agent.run --repo owner/repo --query "Your query here"

# Run the code reflection agent with evaluation
python -m applications.reflection_agent.code_reflection --repo owner/repo --query "Write a function to calculate Fibonacci numbers" --evaluate
```

## Customization

The reflection module is designed to be highly customizable. You can:

- Create custom reflection nodes for specific use cases
- Modify the reflection criteria and prompts
- Integrate with external evaluation tools
- Adjust the maximum number of reflection iterations
- Use different models for the agent and reflection nodes