"""Utility functions for the EMB framework."""

import os
from typing import Any, Dict, Optional

from langsmith import Client


def get_langsmith_client() -> Client:
    """Get a LangSmith client.

    Returns:
        A LangSmith client
    """
    return Client()


def get_langsmith_project() -> str:
    """Get the LangSmith project name.

    Returns:
        The LangSmith project name
    """
    return os.environ.get("LANGCHAIN_PROJECT", "EMB")


def get_environment_variable(name: str, default: Optional[str] = None) -> Optional[str]:
    """Get an environment variable.

    Args:
        name: The name of the environment variable
        default: The default value to return if the environment variable is not set

    Returns:
        The value of the environment variable, or the default value if not set
    """
    return os.environ.get(name, default)