"""Loggers for agents."""

from typing import Any, Dict, List, Optional, Union


class AgentLogger:
    """A logger for agents."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the logger."""
        self.kwargs = kwargs
        
    def log(self, message: str, **kwargs: Any) -> None:
        """Log a message."""
        print(f"[AGENT] {message}")