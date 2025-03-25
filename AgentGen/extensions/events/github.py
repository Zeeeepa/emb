import logging
import os
from typing import Any, Callable, TypeVar

from fastapi import Request

from AgentGen.extensions.github.types.events.base import GitHubEvent