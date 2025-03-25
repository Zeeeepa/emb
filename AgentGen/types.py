"""Type definitions for AgentGen."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Codebase(Protocol):
    """Protocol for Codebase objects.
    
    This allows AgentGen to work with the codegen.Codebase class without
    directly importing it, avoiding circular dependencies.
    """
    
    def __init__(self, path: str):
        ...
    
    @property
    def path(self) -> str:
        """Return the path to the codebase."""
        ...