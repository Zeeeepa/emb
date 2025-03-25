from collections.abc import Generator
from typing import Any, Optional

from langchain.schema import AIMessage, HumanMessage
from langchain.schema import FunctionMessage as LCFunctionMessage

from AgentGen.extensions.tools.base import FunctionMessage