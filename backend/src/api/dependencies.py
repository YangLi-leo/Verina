"""
API Dependencies for Dependency Injection
"""

import logging

from src.services.chat_service import ChatService
from src.services.search_service import SearchService

logger = logging.getLogger(__name__)

# Service instances (in production, these would be properly configured)
_search_service = None
_chat_service = None


def get_search_service() -> SearchService:
    """Get search service instance"""
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service


def get_chat_service() -> ChatService:
    """Get chat service instance"""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
