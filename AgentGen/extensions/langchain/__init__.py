"""Langchain tools for workspace operations."""

from langchain_core.tools.base import BaseTool

from codegen.sdk.core.codebase import Codebase

from .tools import (
    CommitTool,
    CreateFileTool,
    DeleteFileTool,
    EditFileTool,
    ListDirectoryTool,
    RevealSymbolTool,
    RipGrepTool,
    SemanticEditTool,
    ViewFileTool,
)

# Import new extension modules
from . import document_loaders
from . import vector_stores
from . import retrievers
from . import memory
from . import output_parsers

__all__ = [
    # Tool classes
    "CommitTool",
    "CreateFileTool",
    "DeleteFileTool",
    "EditFileTool",
    "ListDirectoryTool",
    "RevealSymbolTool",
    "RipGrepTool",
    "SemanticEditTool",
    "ViewFileTool",
    # Helper functions
    "get_workspace_tools",
    # Extension modules
    "document_loaders",
    "vector_stores",
    "retrievers",
    "memory",
    "output_parsers",
]


def get_workspace_tools(codebase: Codebase) -> list[BaseTool]:
    """Get all workspace tools initialized with a codebase.

    Args:
        codebase: The codebase to operate on

    Returns:
        List of initialized Langchain tools
    """
    return [
        ViewFileTool(codebase),
        ListDirectoryTool(codebase),
        RipGrepTool(codebase),
        EditFileTool(codebase),
        CreateFileTool(codebase),
        DeleteFileTool(codebase),
        CommitTool(codebase),
        RevealSymbolTool(codebase),
        SemanticEditTool(codebase),
    ]
