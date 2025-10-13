"""Deep search tool using Exa for complex queries in deep thinking mode."""

import asyncio
from typing import Any, Dict, List

from src.chat.tools.base import BaseTool
from src.core.config import Config
from src.integrations.search.exa import ExaSearchProvider


class DeepSearchTool(BaseTool):
    """Deep search with Exa for complex queries (deep thinking mode only)."""

    @property
    def name(self) -> str:
        return "deep_search"

    @property
    def description(self) -> str:
        return "Deep parallel search for complex analytical queries, comparisons, and how-to guides"

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Multiple search queries to execute in parallel"
                },
                "num_queries": {
                    "type": "integer",
                    "description": "Number of queries to use (3-5 recommended)",
                    "minimum": 1,
                    "maximum": 5
                }
            },
            "required": ["queries", "num_queries"]
        }

    async def execute(self, queries: List[str], num_queries: int = 3) -> Dict[str, Any]:
        """Execute parallel search with Exa.

        Args:
            queries: List of search queries
            num_queries: Number of queries to actually use

        Returns:
            Dict with candidates, highlights, and metadata
        """
        # Limit queries
        queries = queries[:num_queries]

        try:
            if not Config.EXA_API_KEY:
                return {
                    "success": False,
                    "error": "EXA_API_KEY not configured",
                    "candidates": [],
                    "provider": "exa"
                }

            return await self._search_with_exa(queries)

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "candidates": [],
                "provider": "exa"
            }

    def _build_candidates_with_snake(
        self,
        raw_results: List[Dict[str, Any]],
        max_candidates: int = 12
    ) -> List[Dict[str, Any]]:
        """Build candidates using snake ordering - borrowed from search_engine.py.

        Args:
            raw_results: Flat list of results with 'qid' field
            max_candidates: Maximum number of candidates

        Returns:
            List of candidates with idx assigned
        """
        if not raw_results:
            return []

        # Group by qid while preserving order
        groups: Dict[int, List[Dict[str, Any]]] = {}
        for item in raw_results:
            qid = int(item.get("qid", 1))
            groups.setdefault(qid, []).append(item)

        # Round-robin (snake) interleave for diversity
        ordered: List[Dict[str, Any]] = []
        pointers: Dict[int, int] = {qid: 0 for qid in sorted(groups.keys())}
        qids = sorted(groups.keys())

        while len(ordered) < max_candidates:
            progressed = False
            for qid in qids:
                idx = pointers[qid]
                bucket = groups[qid]
                if idx < len(bucket):
                    ordered.append(bucket[idx])
                    pointers[qid] += 1
                    progressed = True
                    if len(ordered) >= max_candidates:
                        break
            if not progressed:
                break

        # Deduplicate by URL
        seen_urls: set = set()
        candidates: List[Dict[str, Any]] = []

        for raw in ordered:
            url = raw.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            candidate = {
                "idx": 0,  # Will be set below
                "title": (raw.get("title", "") or "").strip(),
                "url": url,
                "snippet": (raw.get("snippet", "") or "").strip(),
                "age": raw.get("age"),  # Always include age (None if not present)
            }

            # Preserve highlights if present
            if "highlights" in raw:
                candidate["highlights"] = raw["highlights"]

            candidates.append(candidate)

            if len(candidates) >= max_candidates:
                break

        # Assign indices - THIS IS THE KEY STEP
        for i, c in enumerate(candidates, start=1):
            c["idx"] = i

        return candidates

    async def _search_with_exa(self, queries: List[str]) -> Dict[str, Any]:
        """Search using Exa for deep content with highlights."""
        async with ExaSearchProvider() as exa:
            tasks = []
            for q in queries:
                tasks.append(
                    exa.search(
                        query=q,
                        num_results=4,
                        include_text=False,  # Use highlights for speed
                        include_highlights=True
                    )
                )

            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build flat list with qid
        raw_results = []
        for qid, res in enumerate(results, start=1):
            if isinstance(res, Exception):
                continue

            for item in res.get("results", []):
                raw_results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                    "highlights": item.get("highlights", [])[:3],  # Keep top 3
                    "age": item.get("age"),  # Published date from Exa
                    "qid": qid
                })

        # Apply snake ordering and deduplication
        candidates = self._build_candidates_with_snake(raw_results)

        # Build highlights for LLM and extract snippet for frontend
        all_highlights = []
        for c in candidates:
            idx = c["idx"]
            age = c.get("age")  # Keep age in candidate

            # Format age for LLM
            age_str = f"({age})" if age else "(Date unknown)"

            if highlights := c.get("highlights", []):  # Keep highlights in candidate for later use
                # Join highlights as snippet for frontend (300-1000 chars)
                joined_highlights = " ".join(highlights)
                if len(joined_highlights) > 1000:
                    c["snippet"] = joined_highlights[:1000] + "..."
                elif len(joined_highlights) >= 300:
                    c["snippet"] = joined_highlights
                # If less than 300, keep original snippet

                # Build highlights for LLM with date
                for h in highlights:
                    all_highlights.append(f"[{idx}] {age_str} {h}")

        merged_sources = "\n---\n".join(all_highlights) if all_highlights else ""

        # Wrap sources in XML structure with Stage 3 guidance
        if merged_sources:
            structured_highlights = f"""<sources>
{merged_sources}
</sources>

Based on the above sources, think step by step about what you found. Wrap your analysis in <analysis> tags."""
        else:
            structured_highlights = ""

        return {
            "success": True,
            "candidates": candidates,
            "highlights": structured_highlights,
            "provider": "exa",
            "num_queries": len(queries),
            "related_searches": []
        }
