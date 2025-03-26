"""Tracing utilities for the EMB framework."""

from typing import Any, Dict, Generator, Iterator, Optional

from emb.agents.loggers import ExternalLogger


class MessageStreamTracer:
    """Tracer for message streams."""

    def __init__(self, logger: Optional[ExternalLogger] = None):
        """Initialize a MessageStreamTracer.

        Args:
            logger: Optional external logger to use
        """
        self.logger = logger

    def process_stream(self, stream: Iterator[Dict[str, Any]]) -> Generator[Dict[str, Any], None, None]:
        """Process a stream of messages.

        Args:
            stream: The stream to process

        Yields:
            The processed messages
        """
        for s in stream:
            # Log the message if a logger is provided
            if self.logger:
                if "messages" in s and len(s["messages"]) > 0:
                    message = s["messages"][-1]
                    if hasattr(message, "content"):
                        self.logger.log_message(
                            f"Agent: {message.content}",
                            metadata={"type": "agent_message"}
                        )
                if "final_answer" in s:
                    self.logger.log_message(
                        f"Final answer: {s['final_answer']}",
                        metadata={"type": "final_answer"}
                    )

            # Yield the message
            yield s