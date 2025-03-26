"""Configuration for the EMB framework."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Config:
    """Configuration for the EMB framework."""

    model_provider: str = "anthropic"
    model_name: str = "claude-3-7-sonnet-latest"
    temperature: float = 0.7
    top_p: float = 0.95
    top_k: Optional[int] = None
    max_tokens: Optional[int] = None
    memory: bool = True
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)