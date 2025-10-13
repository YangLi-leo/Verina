"""Chat module for conversational AI agent with tool calling capabilities."""

from .agent.agent_router import AgentRouter
from .manager import MessageManager
from .prompts import CHAT_AGENT_SYSTEM_PROMPT
from .tools import BaseTool, SandboxTool, WebSearchTool

# Export models (unified frontend-optimized models)
from .model import (
    MessageRole,
    ToolType,
    ThinkingStep,
    MessageDisplay,
    ChatRequest,
    ChatResponse,
    ConversationHistory,
    ErrorResponse,
)

__all__ = [
    # Core
    "AgentRouter",
    "MessageManager",
    # Tools
    "BaseTool",
    "SandboxTool",
    # Prompts
    "CHAT_AGENT_SYSTEM_PROMPT",
    # Models
    "MessageRole",
    "ToolType",
    "ThinkingStep",
    "MessageDisplay",
    "ChatRequest",
    "ChatResponse",
    "ConversationHistory",
    "ErrorResponse",
]
