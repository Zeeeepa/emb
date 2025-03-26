"""Utility functions and classes for the EMB agents."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    system_message: Optional[str] = None
    tools_system_message: Optional[str] = None
    max_iterations: int = 15
    max_execution_time: Optional[int] = None
    verbose: bool = False
    extra_data: Dict[str, Any] = field(default_factory=dict)


def format_message_content(content: Union[str, List[Dict[str, Any]]]) -> str:
    """Format message content for display.

    Args:
        content: The message content to format

    Returns:
        The formatted message content
    """
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        result = []
        for item in content:
            if isinstance(item, dict):
                if "text" in item:
                    result.append(item["text"])
                elif "image_url" in item:
                    result.append("[IMAGE]")
            else:
                result.append(str(item))
        return "\n".join(result)
    else:
        return str(content)