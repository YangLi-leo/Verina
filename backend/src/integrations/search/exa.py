"""Exa Search API provider implementation optimized for LLM applications."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from exa_py import Exa
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ...core.config import Config
from ...core.exceptions import (
    SearchAuthenticationError,
    SearchProviderError,
    SearchRateLimitError,
)
from ...core.logging import get_logger

logger = get_logger(__name__)


class ExaSearchProvider:
    """Exa neural search implementation optimized for AI applications.

    Exa provides neural search capabilities designed specifically for LLMs,
    returning complete content rather than just snippets.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Exa search provider.

        Args:
            api_key: Exa API key. If not provided, uses Config.EXA_API_KEY.
        """
        self.api_key = api_key or Config.EXA_API_KEY
        if not self.api_key:
            raise ValueError("Exa API key not provided and EXA_API_KEY not set")

        self.client = Exa(self.api_key)
        logger.info("Initialized Exa search provider")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type((Exception,)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def search(
        self,
        query: str,
        num_results: int = 10,
        search_type: str = "auto",
        include_text: bool = True,
        include_highlights: bool = True,
        category: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Perform neural search using Exa API with full content retrieval.

        Args:
            query: The search query string.
            num_results: Number of results to return (default: 10).
            search_type: Type of search - "keyword", "neural", "fast", or "auto" (default: "auto").
            include_text: Whether to include full text content (default: True).
            include_highlights: Whether to include highlighted snippets (default: True).
            category: Data category to focus on (e.g., "company", "research paper", "news", etc.).
            **kwargs: Additional parameters for future extensions.

        Returns:
            Dictionary containing:
            - query: The original search query
            - results: List of search results with full content
            - search_type: The type of search used (neural/keyword)

        Raises:
            SearchAuthenticationError: Invalid API key.
            SearchRateLimitError: Rate limit exceeded.
            SearchProviderError: Other API errors.
        """
        try:
            logger.info(
                f"Exa search: query='{query}', num_results={num_results}, type={search_type}"
            )

            loop = asyncio.get_event_loop()

            search_params = {
                "type": search_type,
                "num_results": num_results,
                "text": include_text,
                "highlights": include_highlights,
            }

            if category:
                search_params["category"] = category

            response = await loop.run_in_executor(
                None,
                lambda: self.client.search_and_contents(query, **search_params),
            )

            result_count = len(response.results) if hasattr(response, "results") else 0
            logger.info(f"Exa search completed: retrieved {result_count} results")

            return self._normalize_response(response, query)

        except Exception as e:
            logger.error(f"Exa search error: {str(e)}")
            self._handle_exa_exception(e)

    def _normalize_response(self, exa_response, query: str) -> Dict[str, Any]:
        """Normalize Exa response to match our internal format.

        Args:
            exa_response: Raw response from Exa API
            query: Original search query

        Returns:
            Normalized response dictionary
        """
        normalized_results = []

        for result in exa_response.results:
            normalized_result = {
                "title": getattr(result, "title", ""),
                "url": getattr(result, "url", ""),
                "content": getattr(result, "text", ""),  # Full text content
                "age": getattr(result, "published_date", None),
            }

            if hasattr(result, "author") and result.author:
                normalized_result["author"] = result.author

            if hasattr(result, "highlights") and result.highlights:
                normalized_result["snippet"] = " ... ".join(result.highlights[:3])
                normalized_result["highlights"] = result.highlights
                normalized_result["highlight_scores"] = getattr(
                    result, "highlight_scores", []
                )
            else:
                content = normalized_result["content"]
                if content:
                    normalized_result["snippet"] = (
                        content[:200] + "..." if len(content) > 200 else content
                    )

            normalized_results.append(normalized_result)

        return {
            "query": query,
            "results": normalized_results,
            "search_type": (
                exa_response.resolved_search_type
                if hasattr(exa_response, "resolved_search_type")
                else "auto"
            ),
            "request_id": (
                exa_response.request_id if hasattr(exa_response, "request_id") else None
            ),
        }

    def _handle_exa_exception(self, exception: Exception) -> None:
        """Handle Exa-specific exceptions and convert to our standard exceptions.

        Args:
            exception: The exception from Exa API

        Raises:
            SearchAuthenticationError: Authentication issues
            SearchRateLimitError: Rate limiting
            SearchProviderError: Other errors
        """
        error_msg = str(exception)

        if "unauthorized" in error_msg.lower() or "api key" in error_msg.lower():
            raise SearchAuthenticationError(
                f"Exa authentication failed: {error_msg}",
                status_code=401,
                provider="exa",
            )
        elif "rate limit" in error_msg.lower():
            raise SearchRateLimitError(
                f"Exa rate limit exceeded: {error_msg}", status_code=429, provider="exa"
            )
        elif "not found" in error_msg.lower():
            raise SearchProviderError(
                f"Exa endpoint not found: {error_msg}", status_code=404, provider="exa"
            )
        else:
            raise SearchProviderError(f"Exa search failed: {error_msg}", provider="exa")

    async def get_similar(
        self,
        url: str,
        num_results: int = 10,
        include_text: bool = True,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Find similar pages to a given URL.

        This is a wrapper around Exa's find_similar functionality.

        Args:
            url: The URL to find similar pages for
            num_results: Number of similar results to return
            include_text: Whether to include full text content
            **kwargs: Additional parameters

        Returns:
            Dictionary with similar pages
        """
        try:
            logger.info(f"Exa find similar: url='{url}', num_results={num_results}")

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.find_similar_and_contents(
                    url,
                    num_results=num_results,
                    text=include_text,
                ),
            )

            return self._normalize_response(response, f"Similar to: {url}")

        except Exception as e:
            logger.error(f"Exa find similar error: {str(e)}")
            self._handle_exa_exception(e)
