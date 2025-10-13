"""Data models for SearchAgent V1 - Optimized for streaming and storage."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SearchCandidate(BaseModel):
    """Search result candidate from SearchAgent V1.

    Returned in 'sources' event during streaming.
    Matches output from fast_search and deep_search tools.
    """

    idx: int = Field(..., description="Citation index for [n] references (1-based)")
    title: str = Field(..., description="Page title")
    url: str = Field(..., description="Page URL")
    snippet: str = Field(..., description="Short description (300-1000 chars)")
    age: Optional[str] = Field(
        default=None,
        description="Content age from provider (e.g., '2 months ago', '2024-01-15', or None)"
    )


class SearchAgentResponse(BaseModel):
    """Complete response from SearchAgent.search_stream().

    Returned in final 'complete' event after streaming finishes.
    """

    session_id: str = Field(..., description="Unique session identifier")
    final_answer: str = Field(..., description="Complete AI-generated answer with citations")
    tool_used: Optional[str] = Field(
        default=None,
        description="Tool used: 'fast_search' or 'deep_search'"
    )
    mode: str = Field(..., description="Search mode: 'standard' or 'deep_thinking'")


class SearchAPIResponse(BaseModel):
    """API-level response for database storage and history.

    Combines data from multiple events (sources + complete) for persistence.
    Compatible with SearchRepository and API endpoints.
    """

    # Core identifiers
    search_id: str = Field(..., description="Unique search ID for database indexing")
    user_id: str = Field(..., description="User identifier")
    original_query: str = Field(..., description="User's original search query")
    display_name: Optional[str] = Field(
        None,
        description="LLM-generated concise title for history display (5-10 words)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Search timestamp (UTC)"
    )

    # Search configuration
    mode: str = Field(
        ...,
        description="Search mode: 'standard' or 'deep_thinking'"
    )
    provider: str = Field(
        ...,
        description="Search provider: 'exa-fast', 'exa', 'serper'"
    )
    tool_used: Optional[str] = Field(
        default=None,
        description="Tool used: 'fast_search' or 'deep_search'"
    )

    # Search results
    candidates: List[SearchCandidate] = Field(
        default_factory=list,
        description="Search result candidates"
    )
    related_searches: List[str] = Field(
        default_factory=list,
        description="Related search suggestions"
    )

    # AI answer
    answer: str = Field(..., description="Final AI-generated answer with citations")

    # Legacy compatibility (for old database records)
    queries: List[str] = Field(
        default_factory=list,
        description="Rewritten queries (empty for V1, kept for compatibility)"
    )
    search_session: str = Field(
        default="",
        description="Session context (empty for V1, kept for compatibility)"
    )
