"""Base classes for tools."""

from typing import Any, ClassVar, Dict, List, Optional, Type, Union
from uuid import uuid4

from langchain.schema import BaseMessage
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class FunctionMessage(BaseMessage):
    """A message returned by a function call."""

    type: str = "function"
    name: str
    """The name of the function that was called."""
    result: Union[str, Dict[str, Any]]
    """The result of the function call."""

    @property
    def content(self) -> str:
        """Return the content of the message."""
        if isinstance(self.result, str):
            return self.result
        else:
            return str(self.result)


class CodegenTool(BaseTool):
    """Base class for tools that interact with the codebase."""

    name: ClassVar[str]
    """The name of the tool."""
    description: ClassVar[str]
    """The description of the tool."""
    args_schema: ClassVar[Type[BaseModel]]
    """The schema for the tool's arguments."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the tool."""
        super().__init__(**kwargs)
        self.id = str(uuid4())