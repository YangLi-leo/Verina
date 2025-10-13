"""SearchAgent V1 - Simplified agent-based search."""

from .agent.search_agent import SearchAgent
from .models.search_models import (
    SearchCandidate,
    SearchAPIResponse,
)

__version__ = "1.0.0"

__all__ = [
    "SearchAgent",
    "SearchCandidate",
    "SearchAPIResponse",
]