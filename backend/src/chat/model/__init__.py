"""Chat models module - Unified models optimized for frontend communication.

Architecture:
- base.py: Base enums (MessageRole, ToolType)
- models.py: All chat models (unified for simplicity)
"""

# Base types
from .base import MessageRole, ToolType

# Unified models (frontend-optimized)
from .models import (
    # Internal (MessageManager)
    InternalMessage,
    # Thinking steps (frontend display)
    ThinkingStep,
    # Conversation display
    MessageDisplay,
    # API request/response
    ChatRequest,
    ChatResponse,
    # Session management
    ConversationHistory,
    SessionSummary,
    # Error handling
    ErrorResponse,
)

__all__ = [
    # Base
    "MessageRole",
    "ToolType",
    # Internal
    "InternalMessage",
    # Thinking steps
    "ThinkingStep",
    # Display
    "MessageDisplay",
    # API
    "ChatRequest",
    "ChatResponse",
    # Session
    "ConversationHistory",
    "SessionSummary",
    # Error
    "ErrorResponse",
]