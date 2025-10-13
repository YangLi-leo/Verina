"""SearchAgent V1 - Optimized search pipeline with streaming.

Architecture:
Standard Mode (2 LLM calls):
  Step 1: Tool Call (fast_search) → Sources
  Step 2: Answer Streaming

Deep Thinking Mode (3 LLM calls):
  Step 1: Query Analysis + Tool Call (reasoning + deep_search) → Sources
  Step 2: Extended Thinking (analyze results)
  Step 3: Answer Streaming

Benefits:
- Standard mode: 2 LLM calls (fast tool → answer)
- Deep mode: 3 LLM calls (reasoning+tool → thinking → answer)

Note: Deep exploration (redis tools) handled separately
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional

from src.chat.manager import MessageManager
from src.engines_v1.prompts import (
    SEARCH_AGENT_SYSTEM_PROMPT,
    DEEP_MODE_SYSTEM_PROMPT,
    COMPOSE_ANSWER_PROMPT,
)
from src.engines_v1.tools import FastSearchTool, DeepSearchTool
from src.integrations.llm.openrouter import OpenRouterProvider
from src.core.logging import get_logger

logger = get_logger(__name__)

# Default model for SearchAgent
DEFAULT_SEARCH_MODEL = "google/gemini-2.5-flash-preview-09-2025"


def dedupe_candidates(existing: List[Dict], new_batch: List[Dict]) -> tuple[List[Dict], List[Dict]]:
    """Deduplicate candidates, keeping existing ones unchanged.

    Args:
        existing: First batch of candidates (priority, unchanged)
        new_batch: Second batch to deduplicate against existing

    Returns:
        (merged_candidates, new_only):
            - merged_candidates: All unique candidates with continuous indexing
            - new_only: Only the new candidates (for supplemental highlights)
    """
    existing_urls = {c["url"] for c in existing}
    new_only = [c for c in new_batch if c["url"] not in existing_urls]

    # Merge: existing + new_only (existing keeps their idx unchanged)
    merged = existing + new_only

    # Re-index ONLY the new candidates (starting after existing, 1-based)
    start_idx = len(existing) + 1
    for i, candidate in enumerate(new_only, start=start_idx):
        candidate["idx"] = i

    return merged, new_only


class SearchAgent:
    """
    Search agent with optimized adaptive pipeline.

    Simple queries: Tool → Answer (2 LLM calls)
    Complex queries: Reasoning → Tool → Answer (3 LLM calls)

    The agent automatically determines query complexity and chooses the optimal path.
    Redis tools disabled - deep exploration handled separately.
    """

    def __init__(
        self,
        llm_provider: Optional[OpenRouterProvider] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ):
        """Initialize SearchAgent.

        Args:
            llm_provider: OpenRouter provider instance
            model: Model to use (defaults to DEFAULT_SEARCH_MODEL)
            temperature: Sampling temperature
        """
        self.llm_provider = llm_provider or OpenRouterProvider()
        self.model = model or DEFAULT_SEARCH_MODEL
        self.temperature = temperature

        # Initialize tools (only search tools, no redis)
        self.tools: Dict[str, Any] = {}
        self._initialize_tools()

        # Message manager
        self.message_manager: Optional[MessageManager] = None

        logger.info(f"SearchAgent initialized with {len(self.tools)} tools")

    def _initialize_tools(self):
        """Initialize search tools only."""
        fast_search = FastSearchTool()
        deep_search = DeepSearchTool()

        self.tools[fast_search.name] = fast_search
        self.tools[deep_search.name] = deep_search

        logger.info(f"Initialized tools: {list(self.tools.keys())}")

    def _get_tools_for_openrouter(self) -> List[Dict[str, Any]]:
        """Get tools in OpenRouter format."""
        return [tool.to_openrouter_format() for tool in self.tools.values()]

    async def search_stream(
        self,
        query: str,
        session_id: Optional[str] = None,
        deep_thinking: bool = False,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute search pipeline with streaming.

        Modes:
        1. Standard mode (deep_thinking=False):
           - tool_call → answer (2 LLM calls)
           - Uses fast_search only

        2. Deep thinking mode (deep_thinking=True):
           - reasoning+tool_call → thinking → answer (3 LLM calls)
           - Uses deep_search only

        Args:
            query: User search query
            session_id: Session ID for tracking
            deep_thinking: Enable deep thinking mode (default: False)

        Yields:
            Events:
            - {"type": "metadata", "data": {...}}
            - {"type": "reasoning", "data": "..."} (only for deep thinking mode)
            - {"type": "tool_call", "data": {...}}
            - {"type": "sources", "data": {...}}
            - {"type": "chunk", "data": "..."}
            - {"type": "complete", "data": {...}}
        """
        # Yield metadata
        yield {
            "type": "metadata",
            "data": {
                "model": self.model,
                "temperature": self.temperature,
                "session_id": session_id,
                "mode": "deep_thinking" if deep_thinking else "standard"
            }
        }

        # Initialize message manager with appropriate prompt
        current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if deep_thinking:
            prompt = DEEP_MODE_SYSTEM_PROMPT.format(current_date=current_date)
        else:
            prompt = SEARCH_AGENT_SYSTEM_PROMPT.format(current_date=current_date)

        self.message_manager = MessageManager(prompt)
        self.message_manager.add_user_message(query)

        # Track variables
        tool_name = None
        tool_result = None

        try:
            if not deep_thinking:
                # ============ STANDARD MODE ============
                # Step 1: Direct tool call (fast_search only)
                logger.info("[SearchAgent] Standard mode: Using fast_search")

                response = await self.llm_provider.chat(
                    messages=self.message_manager.get_messages(),
                    model=self.model,
                    temperature=self.temperature,
                    tools=self._get_tools_for_openrouter(),
                    tool_choice={"type": "function", "function": {"name": "fast_search"}},
                )

                message_data = response["choices"][0]["message"]

                # Check if tool was called
                if "tool_calls" in message_data and message_data["tool_calls"]:
                    # Tool called - execute it
                    logger.info("[SearchAgent] Tool called in standard mode")
                    tool_call = message_data["tool_calls"][0]
                    tool_name = tool_call["function"]["name"]
                    tool_args_str = tool_call["function"]["arguments"]

                    logger.info(f"[SearchAgent] Tool: {tool_name}")
                    # Parse arguments
                    try:
                        tool_args = json.loads(tool_args_str)
                    except json.JSONDecodeError as e:
                        error_msg = f"Failed to parse tool arguments: {e}"
                        logger.error(error_msg)
                        yield {"type": "error", "data": error_msg}
                        return

                    # Yield tool call info
                    yield {
                        "type": "tool_call",
                        "data": {
                            "tool": tool_name,
                            "args": tool_args
                        }
                    }

                    # Execute tool
                    tool = self.tools.get(tool_name)
                    if not tool:
                        error_msg = f"Tool '{tool_name}' not found"
                        logger.error(error_msg)
                        yield {"type": "error", "data": error_msg}
                        return

                    tool_result = await tool.execute(**tool_args)

                    # Yield sources (candidates) to frontend
                    if isinstance(tool_result, dict) and "candidates" in tool_result:
                        yield {
                            "type": "sources",
                            "data": {
                                "candidates": tool_result.get("candidates", []),
                                "provider": tool_result.get("provider"),
                                "related_searches": tool_result.get("related_searches", [])
                            }
                        }

                    # Prepare content for LLM - use highlights if available
                    if isinstance(tool_result, dict):
                        highlights = tool_result.get("highlights", "")
                        if highlights:
                            llm_content = highlights
                        else:
                            llm_content = json.dumps(tool_result, ensure_ascii=False, indent=2)
                    else:
                        llm_content = str(tool_result)

                    # Append answer instruction
                    tool_result_with_instruction = (
                        f"{llm_content}\n\n"
                        "Based on the search results above, provide a comprehensive answer "
                        "to the user's query. Include citations using [n] format."
                    )

                    logger.info(f"[SearchAgent] Tool result sent to LLM: {llm_content[:200]}...")

                    # Add to messages
                    self.message_manager.add_assistant_message(tool_calls=message_data["tool_calls"])
                    self.message_manager.add_tool_result(
                        tool_call_id=tool_call["id"],
                        content=tool_result_with_instruction
                    )
                else:
                    error_msg = "No tool was called in standard mode"
                    logger.error(error_msg)
                    yield {"type": "error", "data": error_msg}
                    return

            else:
                # ============ DEEP THINKING MODE ============
                logger.info("[SearchAgent] Deep thinking mode: Three-step pipeline")

                # Step 1: Query Analysis + Tool Call (reasoning content + deep_search call)
                logger.info("[SearchAgent] Step 1: Query analysis + tool call")

                response = await self.llm_provider.chat(
                    messages=self.message_manager.get_messages(),
                    model=self.model,
                    temperature=self.temperature,
                    tools=self._get_tools_for_openrouter(),
                    tool_choice={"type": "function", "function": {"name": "deep_search"}},
                )

                message_data = response["choices"][0]["message"]

                # Check for reasoning content (model can output both content and tool_calls)
                reasoning_content = message_data.get("content", "")
                if reasoning_content:
                    logger.info(f"[SearchAgent] Query reasoning: {reasoning_content[:200]}...")
                    yield {"type": "reasoning", "data": reasoning_content}

                # Check if tool was called
                if "tool_calls" not in message_data or not message_data["tool_calls"]:
                    error_msg = "LLM did not call deep_search in deep mode"
                    logger.error(error_msg)
                    yield {"type": "error", "data": error_msg}
                    return

                tool_call = message_data["tool_calls"][0]
                tool_name = tool_call["function"]["name"]
                tool_args_str = tool_call["function"]["arguments"]

                logger.info(f"[SearchAgent] Tool called: {tool_name}")

                # Parse arguments
                try:
                    tool_args = json.loads(tool_args_str)
                except json.JSONDecodeError as e:
                    error_msg = f"Failed to parse tool arguments: {e}"
                    logger.error(error_msg)
                    yield {"type": "error", "data": error_msg}
                    return

                # Yield tool call info
                yield {
                    "type": "tool_call",
                    "data": {
                        "tool": tool_name,
                        "args": tool_args
                    }
                }

                # Execute tool
                tool = self.tools.get(tool_name)
                if not tool:
                    error_msg = f"Tool '{tool_name}' not found"
                    logger.error(error_msg)
                    yield {"type": "error", "data": error_msg}
                    return

                tool_result = await tool.execute(**tool_args)

                # Store first batch and yield to frontend immediately
                first_batch_candidates = tool_result.get("candidates", []) if isinstance(tool_result, dict) else []
                provider = tool_result.get("provider", "unknown") if isinstance(tool_result, dict) else "unknown"
                related_searches = tool_result.get("related_searches", []) if isinstance(tool_result, dict) else []

                logger.info(f"[SearchAgent] First batch: {len(first_batch_candidates)} candidates")

                # Yield first batch to frontend
                if first_batch_candidates:
                    yield {
                        "type": "sources",
                        "data": {
                            "candidates": first_batch_candidates,
                            "provider": provider,
                            "related_searches": related_searches
                        }
                    }

                # Prepare first batch highlights for LLM
                if isinstance(tool_result, dict):
                    first_highlights = tool_result.get("highlights", "")
                    if not first_highlights:
                        first_highlights = json.dumps(tool_result, ensure_ascii=False, indent=2)
                else:
                    first_highlights = str(tool_result)

                # Save first batch to message history (both reasoning content and tool_calls)
                self.message_manager.add_assistant_message(
                    content=reasoning_content if reasoning_content else None,
                    tool_calls=message_data["tool_calls"]
                )
                self.message_manager.add_tool_result(
                    tool_call_id=tool_call["id"],
                    content=first_highlights
                )

                # Step 2: Mandatory deep exploration with supplemental search
                logger.info("[SearchAgent] Step 2: Mandatory deep exploration (forced supplemental search)")

                response = await self.llm_provider.chat(
                    messages=self.message_manager.get_messages(),
                    model=self.model,
                    temperature=self.temperature,
                    tools=self._get_tools_for_openrouter(),
                    tool_choice={"type": "function", "function": {"name": "deep_search"}},  # Force deep_search
                )

                exploration_msg = response["choices"][0]["message"]
                exploration_reasoning = exploration_msg.get("content", "")

                # Yield exploration reasoning
                if exploration_reasoning:
                    logger.info(f"[SearchAgent] Exploration insight: {exploration_reasoning[:200]}...")
                    yield {"type": "reasoning", "data": exploration_reasoning}

                # Verify tool was called (should always be true with tool_choice)
                if "tool_calls" not in exploration_msg or not exploration_msg["tool_calls"]:
                    error_msg = "LLM did not call deep_search in Stage 2 (mandatory)"
                    logger.error(error_msg)
                    yield {"type": "error", "data": error_msg}
                    return

                logger.info("[SearchAgent] Executing mandatory supplemental search")

                supp_tool_call = exploration_msg["tool_calls"][0]
                supp_tool_name = supp_tool_call["function"]["name"]
                supp_tool_args = json.loads(supp_tool_call["function"]["arguments"])

                # Execute supplemental search
                supp_tool = self.tools.get(supp_tool_name)
                supp_result = await supp_tool.execute(**supp_tool_args)

                second_batch = supp_result.get("candidates", []) if isinstance(supp_result, dict) else []
                logger.info(f"[SearchAgent] Second batch: {len(second_batch)} candidates")

                # Deduplicate: keep first batch unchanged, append only new ones
                merged_candidates, new_only = dedupe_candidates(first_batch_candidates, second_batch)
                logger.info(f"[SearchAgent] After dedup: {len(new_only)} new candidates added")

                # Yield only new candidates to frontend (with correct global indices)
                if new_only:
                    yield {
                        "type": "sources_update",
                        "data": {
                            "candidates": new_only,
                            "action": "append"
                        }
                    }

                # Build highlights for new candidates only (with correct global indices)
                new_highlights_list = []
                for c in new_only:
                    idx = c.get("idx", "?")  # Global index (already set in dedupe_candidates)
                    age = c.get("age")
                    age_str = f"({age})" if age else "(Date unknown)"

                    # Get highlights from original candidate (before popping)
                    # Find matching candidate in second_batch by URL
                    for orig_c in second_batch:
                        if orig_c.get("url") == c.get("url"):
                            if highlights := orig_c.get("highlights", []):
                                for h in highlights:
                                    new_highlights_list.append(f"[{idx}] {age_str} {h}")
                            break

                supp_highlights = "\n".join(new_highlights_list) if new_highlights_list else "No new highlights"
                logger.info(f"[SearchAgent] Built {len(new_highlights_list)} new highlights with correct indices")

                # Save supplemental search to message history (both exploration reasoning and tool_calls)
                self.message_manager.add_assistant_message(
                    content=exploration_reasoning if exploration_reasoning else None,
                    tool_calls=exploration_msg["tool_calls"]
                )
                self.message_manager.add_tool_result(
                    tool_call_id=supp_tool_call["id"],
                    content=supp_highlights
                )

                # Inject prompt to trigger final answer composition
                logger.info("[SearchAgent] Injecting compose answer prompt")
                self.message_manager.add_user_message(COMPOSE_ANSWER_PROMPT)

        except Exception as e:
            logger.error(f"Search execution failed: {e}", exc_info=True)
            yield {"type": "error", "data": f"Search execution failed: {str(e)}"}
            return

        # ============ Answer Streaming Phase ============
        step_num = "Step 2" if not deep_thinking else "Step 3"
        logger.info(f"[SearchAgent] {step_num}: Answer streaming phase")

        try:
            # Stream final answer
            final_chunks = []
            async for chunk in self.llm_provider.chat_stream(
                messages=self.message_manager.get_messages(),
                model=self.model,
                temperature=self.temperature,
            ):
                # Yield to frontend
                yield {"type": "chunk", "data": chunk}
                # Collect for storage
                final_chunks.append(chunk)

            final_answer = "".join(final_chunks)
            self.message_manager.add_assistant_message(content=final_answer)

            logger.info("[SearchAgent] Answer streaming completed")

        except Exception as e:
            logger.error(f"Answer streaming failed: {e}", exc_info=True)
            yield {"type": "error", "data": f"Answer streaming failed: {str(e)}"}
            return

        # ============ Completion ============
        yield {
            "type": "complete",
            "data": {
                "session_id": session_id,
                "final_answer": final_answer,
                "tool_used": tool_name,
                "mode": "deep_thinking" if deep_thinking else "standard"
            }
        }
