"""Codebase class for AgentGen."""

from typing import Any, Dict, List, Optional, Union


class Codebase:
    """A class representing a codebase."""

    def __init__(self, path: str, **kwargs: Any) -> None:
        """Initialize the codebase.
        
        Args:
            path: The path to the codebase.
            **kwargs: Additional arguments to pass to the codebase.
        """
        self.path = path
        self.kwargs = kwargs
        
    def __repr__(self) -> str:
        """Return a string representation of the codebase."""
        return f"Codebase(path={self.path})"