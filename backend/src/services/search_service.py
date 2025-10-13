"""
Search Service - API adapter for SearchAgent V1
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import uuid4

from src.core.config import Config
from src.engines_v1.agent.search_agent import SearchAgent
from src.engines_v1.models.search_models import SearchAPIResponse
from src.integrations.llm.openrouter import OpenRouterProvider

logger = logging.getLogger(__name__)


class SearchService:
    """
    Search service - API adapter for SearchAgent V1 with event transformation
    """

    def __init__(self):
        self.llm_provider = OpenRouterProvider()

        self.search_agent = SearchAgent(llm_provider=self.llm_provider)

        self.base_dir = Path(Config.DATA_BASE_DIR).expanduser()

        self.search_records: Dict[str, Dict[str, Any]] = {}

        self._load_existing_searches()

    def _load_existing_searches(self):
        """Load all existing search records from file system on startup.

        Scans base_dir/searches/ directory and populates self.search_records
        so that history API returns all searches even after server restart.
        """
        try:
            searches_dir = self.base_dir / "searches"

            if not searches_dir.exists():
                logger.info("No searches directory found, starting fresh")
                return

            loaded_count = 0

            for search_dir in searches_dir.iterdir():
                if not search_dir.is_dir():
                    continue

                search_id = search_dir.name
                search_file = search_dir / "search_result.json"

                if not search_file.exists():
                    logger.debug(f"Skipping {search_id} - no search_result.json")
                    continue

                try:
                    with open(search_file, 'r', encoding='utf-8') as f:
                        search_record = json.load(f)

                    self.search_records[search_id] = search_record
                    loaded_count += 1

                except Exception as e:
                    logger.error(f"Failed to load search {search_id}: {e}")
                    continue

            logger.info(f"Loaded {loaded_count} existing search records from file system")

        except Exception as e:
            logger.error(f"Failed to load existing searches: {e}", exc_info=True)

    async def search(
        self,
        user_id: str,
        query: str,
        deep_thinking: bool = False
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute search with streaming using SearchAgent V1

        Args:
            user_id: User identifier
            query: Search query
            deep_thinking: Enable deep thinking mode

        Yields:
            Events: metadata, chunk, done
        """
        try:
            search_id = f"search_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
            mode = "deep_thinking" if deep_thinking else "standard"
            logger.info(f"[SearchService] Starting search {search_id} for user {user_id}, mode={mode}, query: {query[:50]}...")

            candidates = []
            provider = "unknown"
            related_searches = []
            answer = ""
            tool_used = None

            async for event in self.search_agent.search_stream(
                query=query,
                session_id=search_id,
                deep_thinking=deep_thinking
            ):
                event_type = event.get("type")

                if event_type in ["metadata", "reasoning", "tool_call"]:
                    continue

                elif event_type == "sources":
                    data = event.get("data", {})
                    candidates = data.get("candidates", [])
                    provider = data.get("provider", "unknown")
                    related_searches = data.get("related_searches", [])

                    logger.info(f"[SearchService] Received {len(candidates)} initial candidates from {provider}")

                    yield {
                        "type": "metadata",
                        "data": {
                            "search_id": search_id,
                            "original_query": query,
                            "queries": [],
                            "candidates": candidates,
                            "related_searches": related_searches,
                        }
                    }

                elif event_type == "sources_update":
                    data = event.get("data", {})
                    new_candidates = data.get("candidates", [])

                    logger.info(f"[SearchService] Received {len(new_candidates)} supplemental candidates")

                    yield {
                        "type": "metadata_update",
                        "data": {
                            "candidates": new_candidates,
                            "action": data.get("action", "append")
                        }
                    }

                elif event_type == "chunk":
                    chunk = event.get("data", "")
                    answer += chunk
                    yield {"type": "chunk", "content": chunk}

                elif event_type == "complete":
                    complete_data = event.get("data", {})
                    tool_used = complete_data.get("tool_used")

                    display_name = await self._generate_display_name(
                        query=query,
                        answer_preview=answer[:200] if answer else ""
                    )

                    from src.engines_v1.models import SearchAPIResponse

                    response = SearchAPIResponse(
                        search_id=search_id,
                        user_id=user_id,
                        original_query=query,
                        display_name=display_name,
                        timestamp=datetime.now(timezone.utc),
                        mode=mode,
                        provider=provider,
                        tool_used=tool_used,
                        candidates=candidates,
                        related_searches=related_searches,
                        answer=answer,
                        queries=[],
                        search_session="",
                    )

                    # Use mode='json' to serialize datetime objects to ISO strings
                    await self._save_search_record(response.model_dump(mode='json'))
                    logger.info(f"[SearchService] Search {search_id} completed, display_name='{display_name}', answer_length={len(answer)}, tool={tool_used}")

                elif event_type == "error":
                    error_msg = event.get("data", "Unknown error")
                    logger.error(f"[SearchService] Search {search_id} error: {error_msg}")
                    yield {"type": "error", "message": error_msg}
                    return

        except Exception as e:
            logger.error(f"[SearchService] Search error: {e}", exc_info=True)
            raise

    async def close(self):
        """Clean up resources"""
        if hasattr(self.llm_provider, "close"):
            await self.llm_provider.close()

    async def _save_search_record(self, search_record: Dict[str, Any]):
        """Save search record to directory structure (search_id as top-level folder)."""
        try:
            search_id = search_record.get("search_id")
            if search_id:
                self.search_records[search_id] = search_record

                search_dir = self.base_dir / "searches" / search_id
                search_dir.mkdir(parents=True, exist_ok=True)

                (search_dir / "sessions").mkdir(exist_ok=True)
                (search_dir / "workspace").mkdir(exist_ok=True)

                search_file = search_dir / "search_result.json"
                with open(search_file, 'w', encoding='utf-8') as f:
                    json.dump(search_record, f, ensure_ascii=False, indent=2)

                logger.info(f"Saved search record to directory: {search_id}")
        except Exception as e:
            logger.error(f"Failed to save search record: {e}")


    async def _generate_display_name(self, query: str, answer_preview: str = "") -> str:
        """Generate a concise display name for search history using LLM.

        Args:
            query: Original search query
            answer_preview: Optional preview of the answer (first 200 chars)

        Returns:
            Concise 10-20 word title for history display
        """
        try:
            prompt = f"""Generate a concise, clear title (10-20 words) for this search query.
The title should capture the main topic or question being asked.

Query: {query}
{f'Answer preview: {answer_preview[:200]}...' if answer_preview else ''}

Requirements:
- 10-20 words
- Clear and descriptive
- No quotes or special formatting
- Capitalize like a title

Title:"""

            response = await self.llm_provider.generate(
                messages=[{"role": "user", "content": prompt}],
                model="openai/gpt-5-chat",
                temperature=0.3,  # Lower temperature for consistent titles
                max_tokens=60,  # Enough for 10-20 words
            )

            display_name = response.get("content", "").strip()

            if not display_name or len(display_name) < 3:
                display_name = query[:80] + ("..." if len(query) > 80 else "")

            logger.info(f"Generated display_name: '{display_name}' for query: '{query[:50]}'")
            return display_name

        except Exception as e:
            logger.error(f"Failed to generate display_name: {e}")
            return query[:80] + ("..." if len(query) > 80 else "")

    async def get_search_record(
        self, search_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get specific search record for history restoration (with user verification)."""
        search_record = self.search_records.get(search_id)

        if not search_record:
            try:
                search_file = SEARCH_STORAGE_DIR / search_id / "search_result.json"
                if search_file.exists():
                    with open(search_file, 'r', encoding='utf-8') as f:
                        search_record = json.load(f)
                    self.search_records[search_id] = search_record
                    logger.info(f"Loaded search record from directory: {search_id}")
            except Exception as e:
                logger.error(f"Failed to load search record from file: {e}")

        # Verify user ownership
        if search_record and search_record.get("user_id") == user_id:
            return search_record
        return None

    async def get_search_record_public(self, search_id: str) -> Optional[Dict[str, Any]]:
        """Get search record without user verification (public access via search_id).

        Note: search_id itself acts as an access token (UUID is hard to guess)
        """
        search_record = self.search_records.get(search_id)

        if not search_record:
            try:
                search_file = self.base_dir / "searches" / search_id / "search_result.json"
                if search_file.exists():
                    with open(search_file, 'r', encoding='utf-8') as f:
                        search_record = json.load(f)
                    self.search_records[search_id] = search_record
                    logger.info(f"Loaded search record from directory: {search_id}")
            except Exception as e:
                logger.error(f"Failed to load search record from file: {e}")

        return search_record

    async def get_user_search_history(
        self, user_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get user's search history for history sidebar."""
        user_searches = []
        for record in self.search_records.values():
            if record.get("user_id") == user_id:
                # Extract the essential fields for history display
                user_searches.append({
                    "search_id": record.get("search_id"),
                    "query": record.get("original_query"),  # Note: field name is original_query
                    "display_name": record.get("display_name"),  # LLM-generated title
                    "timestamp": record.get("timestamp"),
                })

        # Sort by timestamp (newest first) and limit
        user_searches.sort(key=lambda x: x.get("timestamp"), reverse=True)
        return user_searches[:limit]
