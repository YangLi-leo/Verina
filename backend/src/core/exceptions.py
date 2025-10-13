"""Core exceptions for the Verina platform.

This module contains all custom exceptions used throughout the application.
Organized by category for clarity.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# Base Exception
class VerinaError(Exception):
    """Base exception for all Verina errors."""
    
    def __init__(self, message: str):
        super().__init__(message)
        logger.error(f"{self.__class__.__name__}: {message}")


# LLM Provider Exceptions
class LLMProviderError(VerinaError):
    """Error communicating with LLM provider."""
    
    def __init__(self, message: str, status_code: int = None, provider: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.provider = provider


class AuthenticationError(LLMProviderError):
    """Authentication failed with provider (401)."""
    pass


class InsufficientCreditsError(LLMProviderError):
    """Insufficient credits/quota (402)."""
    pass


class RateLimitError(LLMProviderError):
    """Rate limit exceeded (429)."""
    pass


class ModelUnavailableError(LLMProviderError):
    """Requested model is unavailable (502/503)."""
    pass


# Search Provider Exceptions
class SearchProviderError(VerinaError):
    """Error communicating with search provider."""
    
    def __init__(self, message: str, status_code: int = None, provider: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.provider = provider


class SearchAuthenticationError(SearchProviderError):
    """Authentication failed with search provider (401)."""
    pass


class SearchRateLimitError(SearchProviderError):
    """Rate limit exceeded for search provider (429)."""
    pass


# Agent Exceptions (Future)
class AgentError(VerinaError):
    """Base exception for agent-related errors."""
    pass


# Session Exceptions (Future)
class SessionError(VerinaError):
    """Base exception for session management errors."""
    pass