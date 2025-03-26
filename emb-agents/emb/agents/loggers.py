"""Logging utilities for the EMB framework."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExternalLogger(ABC):
    """Abstract base class for external loggers."""

    @abstractmethod
    def log_message(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log a message to an external service.

        Args:
            message: The message to log
            metadata: Optional metadata to include with the message
        """
        pass


class ConsoleLogger(ExternalLogger):
    """Logger that logs messages to the console."""

    def log_message(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log a message to the console.

        Args:
            message: The message to log
            metadata: Optional metadata to include with the message
        """
        if metadata:
            logger.info(f"{message} (metadata: {metadata})")
        else:
            logger.info(message)


class SlackLogger(ExternalLogger):
    """Logger that logs messages to Slack."""

    def __init__(self, webhook_url: str, channel: str):
        """Initialize a SlackLogger.

        Args:
            webhook_url: The Slack webhook URL to use
            channel: The Slack channel to log to
        """
        self.webhook_url = webhook_url
        self.channel = channel

    def log_message(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log a message to Slack.

        Args:
            message: The message to log
            metadata: Optional metadata to include with the message
        """
        # This would be implemented using the Slack API
        logger.info(f"Logging to Slack: {message}")
        if metadata:
            logger.info(f"Metadata: {metadata}")


class CompositeLogger(ExternalLogger):
    """Logger that logs messages to multiple loggers."""

    def __init__(self, loggers: list[ExternalLogger]):
        """Initialize a CompositeLogger.

        Args:
            loggers: The loggers to log to
        """
        self.loggers = loggers

    def log_message(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log a message to all loggers.

        Args:
            message: The message to log
            metadata: Optional metadata to include with the message
        """
        for logger in self.loggers:
            logger.log_message(message, metadata)