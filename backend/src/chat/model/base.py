"""Base types and enums for chat models."""

from enum import Enum


class MessageRole(str, Enum):
    """Message roles in conversation"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolType(str, Enum):
    """Types of tools available in ChatAgent"""
    WEB_SEARCH = "web_search"
    EXECUTE_PYTHON = "execute_python"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"