"""Web Search Tool - Search the web using Exa neural search."""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseTool
from src.integrations.search.exa import ExaSearchProvider

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    """Web search tool powered by Exa neural search.

    Provides semantic search capabilities designed for AI applications,
    returning full content and automatically caching to workspace.
    """

    def __init__(self, workspace_dir: Optional[Path] = None):
        """Initialize web search tool.

        Args:
            workspace_dir: Optional workspace directory for caching search results
        """
        self.search_provider = ExaSearchProvider()
        self.workspace_dir = workspace_dir

    @property
    def name(self) -> str:
        """Tool name."""
        return "web_search"

    @property
    def description(self) -> str:
        """Tool description."""
        return (
            "Web search that automatically caches full article content. "
            "Returns titles, URLs, highlights, and saves complete content to cache/. "
            "Use this first to gather sources. Review highlights to decide which articles are useful. "
            "Use file_read to access cached articles, or research_assistant for deep analysis."
        )

    def get_parameters(self) -> Dict[str, Any]:
        """Define tool parameters."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query. Be specific and use natural language."
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5, max: 10)",
                    "minimum": 1,
                    "maximum": 10
                },
                "search_type": {
                    "type": "string",
                    "enum": ["auto", "neural", "keyword", "fast"],
                    "description": (
                        "Type of search: 'neural' uses embeddings (semantic), "
                        "'keyword' is like Google SERP (exact match), "
                        "'fast' uses streamlined models, "
                        "'auto' (default) intelligently combines neural and keyword."
                    )
                },
                "category": {
                    "type": "string",
                    "enum": [
                        "company",
                        "research paper",
                        "news",
                        "pdf",
                        "github",
                        "tweet",
                        "personal site",
                        "linkedin profile",
                        "financial report"
                    ],
                    "description": (
                        "Focus search on a specific data category for higher quality results. "
                        "Examples: 'company' for business info, 'research paper' for academic content, "
                        "'news' for current events, 'github' for code repositories."
                    )
                }
            },
            "required": ["query"]
        }

    def _sanitize_filename(self, title: str, max_length: int = 100) -> str:
        """Sanitize title to create a valid filename."""
        if not title:
            return "untitled"

        sanitized = re.sub(r'[^\w\s-]', '', title)
        sanitized = re.sub(r'\s+', '_', sanitized)
        sanitized = re.sub(r'_+', '_', sanitized)
        sanitized = sanitized[:max_length].strip('_')

        return sanitized if sanitized else "untitled"

    async def execute(
        self,
        query: str,
        num_results: int = 5,
        search_type: str = "auto",
        category: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute web search.

        Args:
            query: Search query string
            num_results: Number of results to return (1-10)
            search_type: Type of search - "auto", "neural", "keyword", or "fast"
            category: Optional data category to focus on
            **kwargs: Additional arguments (ignored)

        Returns:
            Dict with raw search results for ChatAgent to process
        """
        try:
            num_results = max(1, min(num_results, 10))

            logger.info(
                f"Web search: query='{query}', num_results={num_results}, "
                f"type={search_type}, category={category}"
            )

            response = await self.search_provider.search(
                query=query,
                num_results=num_results,
                search_type=search_type,
                category=category,
                include_text=True,  # Get full content for caching
                include_highlights=True
            )

            if not response.get("results"):
                return {
                    "query": query,
                    "search_type": response.get('search_type', 'auto'),
                    "results": []
                }

            normalized_results = []
            for result in response["results"]:
                highlights = result.get("highlights", [])
                snippet = " ".join(highlights) if highlights else ""

                title = result.get("title", "N/A")
                url = result.get("url", "")
                content = result.get("content", "")

                cache_path = None
                if self.workspace_dir and content:
                    try:
                        cache_dir = self.workspace_dir / "cache"
                        cache_dir.mkdir(parents=True, exist_ok=True)

                        safe_filename = self._sanitize_filename(title)
                        file_path = cache_dir / f"{safe_filename}.md"

                        counter = 1
                        while file_path.exists():
                            file_path = cache_dir / f"{safe_filename}_{counter}.md"
                            counter += 1

                        age_str = result.get("age", "")
                        file_content = f"""# {title}

**URL**: {url}
**Published**: {age_str}

---

{content}"""
                        file_path.write_text(file_content, encoding="utf-8")
                        cache_path = str(file_path.relative_to(self.workspace_dir))
                        logger.info(f"Cached with metadata: {cache_path}")
                    except Exception as e:
                        logger.warning(f"Failed to cache content: {e}")

                normalized_results.append({
                    "url": url,
                    "title": title,
                    "snippet": snippet if snippet else "",
                    "age": result.get("age"),
                    "cache_path": cache_path
                })

            logger.info(f"Web search completed: {len(normalized_results)} results returned, {sum(1 for r in normalized_results if r.get('cache_path'))} cached")

            return {
                "query": query,
                "search_type": response.get('search_type', 'auto'),
                "results": normalized_results
            }

        except Exception as e:
            error_msg = f"Web search failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "query": query,
                "search_type": "error",
                "results": [],
                "error": error_msg
            }
