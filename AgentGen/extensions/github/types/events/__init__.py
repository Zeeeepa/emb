"""GitHub event types."""

from .pull_request import PullRequestEvent
from .push import PushEvent

__all__ = ["PullRequestEvent", "PushEvent"]