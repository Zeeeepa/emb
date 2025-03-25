"""Utilities for agents."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    model_name: str = "gpt-4"
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0