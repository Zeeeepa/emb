from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal, Optional, Union

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from AgentGen.extensions.tools.base import FunctionMessage