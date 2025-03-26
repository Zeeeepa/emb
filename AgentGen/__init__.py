"""
AgentGen - A framework for creating code agents
"""

# Import core agent classes
from .agents.code_agent import CodeAgent
from .agents.chat_agent import ChatAgent

# Import agent creation functions
from .agents.factory import (
    create_agent_with_tools,
    create_codebase_agent,
    create_codebase_inspector_agent,
    create_chat_agent,
)

__version__ = "0.1.0"

__all__ = [
    "CodeAgent",
    "ChatAgent",
    "create_agent_with_tools",
    "create_codebase_agent",
    "create_codebase_inspector_agent",
    "create_chat_agent",
]