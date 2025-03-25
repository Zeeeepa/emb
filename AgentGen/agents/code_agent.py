import os
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from langchain.tools import BaseTool
from langchain_core.messages import AIMessage

from AgentGen import Codebase

if TYPE_CHECKING:
    from langchain_core.language_models import BaseLanguageModel

from .data import AgentRunMessage
from .loggers import AgentLogger
from .tracer import AgentTracer
from .utils import AgentConfig