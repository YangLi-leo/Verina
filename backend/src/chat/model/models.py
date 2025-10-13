"""Unified chat models - Optimized for frontend data transmission.

This module consolidates all chat-related models for clean frontend-backend communication.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from .base import MessageRole


# Internal conversation state models

class InternalMessage(BaseModel):
    """Internal message format for MessageManager - matches OpenRouter API format.

    This is used internally by MessageManager and sent to LLM.
    """
    role: MessageRole = Field(..., description="Message role")
    content: Optional[str] = Field(None, description="Message content (None for tool calls)")

    # Tool-related fields (OpenRouter format)
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Tool calls from LLM in OpenRouter format"
    )
    tool_call_id: Optional[str] = Field(
        None,
        description="Tool call ID for tool result messages"
    )


# Frontend display models

class ThinkingStep(BaseModel):
    """Single step in the thinking chain - optimized for frontend display.

    Represents one tool execution in the ReAct loop.
    """
    step: int = Field(..., description="Step number (1-based)")
    tool: str = Field(..., description="Tool name: web_search | execute_python | file_read | file_write | etc.")
    input: Dict[str, Any] = Field(..., description="Tool input parameters")
    output: str = Field(..., description="Tool execution result")
    success: bool = Field(True, description="Whether execution succeeded")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    # GPT-5 reasoning field (internal thought process, not sent to context)
    thinking: Optional[str] = Field(None, description="LLM's internal reasoning (from GPT-5 reasoning field)")

    # Optional metadata for specific tools
    urls: Optional[List[str]] = Field(None, description="URLs accessed (for web tools)")
    has_code: bool = Field(False, description="Whether output contains code")
    has_image: bool = Field(False, description="Whether output contains image")


class MessageDisplay(BaseModel):
    """Message format for frontend chat display.

    Simplified format for rendering messages in chat UI.
    """
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content for display")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    # Optional thinking steps (only for assistant messages with tools)
    thinking_steps: Optional[List[ThinkingStep]] = Field(
        None,
        description="Thinking steps if assistant used tools"
    )


# API request/response models

class ChatRequest(BaseModel):
    """Request from frontend to send a message."""
    message: str = Field(..., min_length=1, max_length=2000, description="User's message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")

    # Mode selection: "chat" for standard mode, "agent" for research mode
    mode: Optional[str] = Field("chat", description="Operation mode: 'chat' (default) or 'agent'")

    # Optional parameters
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Override default temperature")
    max_iterations: Optional[int] = Field(None, ge=1, le=10, description="Override max ReAct iterations")


class ChatResponse(BaseModel):
    """Response from ChatAgent - optimized for frontend consumption.

    This is the unified response model returned by both ChatAgent.chat() and API endpoints.
    """
    model_config = {"protected_namespaces": ()}

    # Response identifier (unique for each user-assistant exchange)
    response_id: str = Field(..., description="Unique identifier for this response")

    # Session info
    session_id: str = Field(..., description="Session ID for this conversation")
    user_id: str = Field(..., description="User identifier")

    # Message content
    user_message: str = Field(..., description="Original user message")
    assistant_message: str = Field(..., description="Assistant's final response")

    # Mode
    mode: str = Field("chat", description="Operation mode: 'chat' or 'agent'")

    # Thinking process (for frontend to display step-by-step)
    thinking_steps: Optional[List[ThinkingStep]] = Field(
        None,
        description="Thinking steps if tools were used"
    )

    # Summary metadata
    used_tools: bool = Field(False, description="Whether any tools were used")
    has_code: bool = Field(False, description="Whether response contains code execution")
    has_web_results: bool = Field(False, description="Whether response contains web search results")

    # Performance metrics
    total_time_ms: int = Field(..., description="Total processing time")
    model_used: str = Field(..., description="LLM model used")
    temperature: float = Field(..., description="Temperature parameter")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    # Context size tracking
    prompt_tokens: Optional[int] = Field(None, description="Total prompt tokens (context size)")

    # Sources for citation (from web_search results in this round)
    sources: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Citation sources for [1][2] references. Format: [{idx: 1, title: '...', url: '...', snippet: '...'}, ...]"
    )

    # Artifact (for HTML blog, charts, etc.)
    artifact: Optional[Dict[str, Any]] = Field(
        None,
        description="Generated artifact (HTML blog, visualization, etc.)"
    )


# Session management models

class ConversationHistory(BaseModel):
    """Full conversation history for a session.

    Used when frontend requests to load a previous conversation.
    """
    session_id: str = Field(..., description="Session identifier")
    messages: List[MessageDisplay] = Field(..., description="All messages in conversation")
    total_messages: int = Field(..., description="Message count")
    created_at: datetime = Field(..., description="When conversation started")
    updated_at: datetime = Field(..., description="Last message timestamp")


class SessionSummary(BaseModel):
    """Summary of a chat session for history sidebar.

    Lightweight model for listing user's conversations.
    """
    session_id: str = Field(..., description="Session identifier")
    preview: str = Field(..., description="First message preview")
    message_count: int = Field(..., description="Number of messages")
    last_updated: datetime = Field(..., description="Last activity timestamp")


# Error response model

class ErrorResponse(BaseModel):
    """Structured error response."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    session_id: Optional[str] = Field(None, description="Session ID if available")
    timestamp: datetime = Field(default_factory=datetime.utcnow)