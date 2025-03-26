"""Base agent implementation for the EMB framework."""

from typing import Any, Dict, List, Optional, Union

from emb.core.config import Config


class BaseAgent:
    """Base agent implementation for the EMB framework."""

    def __init__(self, config: Config):
        """Initialize a BaseAgent.

        Args:
            config: Configuration for the agent
        """
        self.config = config

    def run(self, prompt: str, **kwargs: Any) -> str:
        """Run the agent with a prompt.

        Args:
            prompt: The prompt to run
            **kwargs: Additional arguments to pass to the agent

        Returns:
            The agent's response
        """
        raise NotImplementedError("Subclasses must implement this method")