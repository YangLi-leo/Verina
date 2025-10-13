"""Base Agent - Shared functionality for ChatModeAgent and AgentModeAgent.

This base class extracts common code to reduce duplication:
- Directory and workspace management
- Chat history persistence
- Tool execution logic
- Sources tracking for citations
- Cleanup methods
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.chat.config import ChatConfig
from src.chat.model import ThinkingStep
from src.core.config import Config
from src.integrations.llm.openrouter import OpenRouterProvider

logger = logging.getLogger(__name__)


class BaseAgent:
    """
    Base class for Chat Mode and Agent Mode agents.

    Provides shared functionality:
    - Workspace and directory management
    - Chat history persistence
    - Tool execution
    - Sources tracking
    - Cleanup methods
    """

    def __init__(
        self,
        llm_provider: Optional[OpenRouterProvider] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_iterations: int = None,
        session_id: Optional[str] = None,
        base_data_dir: Optional[Path] = None,
        workspace_suffix: str = "",  # "workspace_chat" or "workspace_agent"
    ):
        """Initialize Base Agent.

        Args:
            llm_provider: OpenRouter provider instance
            model: Model to use
            temperature: Sampling temperature
            max_iterations: Maximum ReAct iterations
            session_id: Session identifier (independent chat ID)
            base_data_dir: Base directory for data storage
            workspace_suffix: Workspace directory suffix (chat or agent)
        """
        self.llm_provider = llm_provider or OpenRouterProvider()
        self.model = model or ChatConfig.DEFAULT_MODEL
        self.temperature = temperature
        self.max_iterations = max_iterations or ChatConfig.MAX_ITERATIONS
        self.session_id = session_id

        if session_id:
            data_base = base_data_dir if base_data_dir is not None else Path(Config.DATA_BASE_DIR).expanduser()
            self.search_base_dir = data_base / "chats" / session_id
            self.workspace_dir = self.search_base_dir / workspace_suffix if workspace_suffix else None
            self.chat_history_file = self.search_base_dir / "chat_history.json"
        else:
            self.search_base_dir = None
            self.workspace_dir = None
            self.chat_history_file = None

        self.current_sources: List[Dict] = []
        self.chat_history = self._load_chat_history()

    def _initialize_workspace(self):
        """Initialize workspace directory structure."""
        if not self.workspace_dir:
            return

        logger.info(f"Initializing workspace at {self.workspace_dir}")

        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        (self.workspace_dir / "cache").mkdir(exist_ok=True)
        (self.workspace_dir / "analysis" / "images").mkdir(parents=True, exist_ok=True)
        (self.workspace_dir / "analysis" / "data").mkdir(parents=True, exist_ok=True)

    def _load_chat_history(self) -> Dict:
        """Load existing chat history or create new."""
        if not self.chat_history_file:
            return self._create_empty_history()

        if self.chat_history_file.exists():
            try:
                with open(self.chat_history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load chat history: {e}")

        return self._create_empty_history()

    def _create_empty_history(self) -> Dict:
        """Create empty chat history structure."""
        return {
            "session_id": self.session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "responses": []
        }

    def _save_chat_history(self):
        """Persist chat history to disk."""
        if not self.chat_history_file:
            return

        try:
            self.chat_history["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.chat_history_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.chat_history_file, 'w', encoding='utf-8') as f:
                json.dump(self.chat_history, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved chat history with {len(self.chat_history['responses'])} responses")
        except Exception as e:
            logger.error(f"Failed to save chat history: {e}")

    def _add_response_to_history(
        self,
        user_message: str,
        assistant_message: str,
        sources: List[Dict],
        thinking_steps: Optional[List[ThinkingStep]],
        total_time_ms: int,
        mode: str,
        prompt_tokens: Optional[int] = None,
        artifact: Optional[Dict] = None,
        stage: Optional[str] = None,
    ) -> str:
        """Add a response to chat history.

        Args:
            user_message: User's message
            assistant_message: Assistant's response
            sources: List of sources for citations
            thinking_steps: List of thinking steps from tool execution
            total_time_ms: Total processing time
            mode: "chat" or "agent"
            prompt_tokens: Number of tokens in prompt (optional)
            artifact: HTML artifact if generated (optional)
            stage: Agent stage ("hil" or "research") - only for agent mode

        Returns:
            The generated response_id
        """
        # Reload chat history from file to ensure we have the latest state
        # This is crucial when switching between chat/agent modes
        self.chat_history = self._load_chat_history()

        # Generate unique response_id with timestamp + short random
        response_id = f"resp_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        response_entry = {
            "response_id": response_id,
            "user_message": user_message,
            "assistant_message": assistant_message,
            "sources": sources,
            "thinking_steps": [step.model_dump(mode='json') for step in thinking_steps] if thinking_steps else None,
            "mode": mode,
            "used_tools": len(sources) > 0 or (thinking_steps is not None and len(thinking_steps) > 0),
            "has_code": thinking_steps and any(step.has_code for step in thinking_steps),
            "has_web_results": len(sources) > 0,
            "total_time_ms": total_time_ms,
            "model_used": self.model,
            "temperature": self.temperature,
            "prompt_tokens": prompt_tokens,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if artifact:
            response_entry["artifact"] = artifact
        if stage:
            response_entry["stage"] = stage

        self.chat_history["responses"].append(response_entry)
        self._save_chat_history()

        return response_id

    def _process_web_search_result(self, result: Dict) -> Tuple[str, List[Dict]]:
        """Process web_search result with sources tracking for [1][2] citations.

        Args:
            result: Web search result from WebSearchTool

        Returns:
            Tuple of (formatted_text_for_llm, sources_for_frontend)
        """
        if result.get("error") or not result.get("results"):
            error_text = result.get("error", "No results found")
            return (f"Search failed: {error_text}", [])

        sources = []
        formatted_lines = [
            f"Search query: {result['query']}",
            f"Found {len(result['results'])} results",
            f"Search type: {result.get('search_type', 'auto')}",
            "\n" + "=" * 80 + "\n",
        ]

        for idx, r in enumerate(result["results"], 1):
            source = {
                "idx": idx,
                "title": r["title"],
                "url": r["url"],
                "snippet": r.get("snippet", ""),
                "age": r.get("age"),
                "cache_path": r.get("cache_path")
            }
            sources.append(source)

            formatted_lines.append(f"[{idx}] {r['title']}")
            formatted_lines.append(f"    URL: {r['url']}")
            if r.get("cache_path"):
                formatted_lines.append(f"    Cached: {r['cache_path']}")
            if r.get("age"):
                formatted_lines.append(f"    Published: {r['age']}")
            if r.get("snippet"):
                formatted_lines.append(f"    {r['snippet']}")
            formatted_lines.append("")

        formatted_text = "\n".join(formatted_lines)
        self.current_sources = sources

        return (formatted_text, sources)

    async def _execute_tool(self, tool_call: Dict[str, Any], tools: Dict) -> Tuple[str, Optional[List[Dict]]]:
        """Execute a single tool call.

        Args:
            tool_call: Tool call dict from LLM
            tools: Dict of available tools

        Returns:
            Tuple of (result_text, sources_if_web_search)
        """
        tool_name = tool_call["function"]["name"]
        tool_args_str = tool_call["function"]["arguments"]

        try:
            tool_args = json.loads(tool_args_str)
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse tool arguments: {e}"
            logger.error(error_msg)
            return (error_msg, None)

        tool = tools.get(tool_name)
        if not tool:
            error_msg = f"Tool '{tool_name}' not found"
            logger.error(error_msg)
            return (error_msg, None)

        try:
            logger.info(f"Executing tool '{tool_name}' with args: {tool_args}")
            result = await tool.execute(**tool_args)

            if tool_name == "web_search":
                # Special processing for web_search to extract sources
                return self._process_web_search_result(result)
            elif tool_name.startswith("mcp_"):
                if isinstance(result, dict):
                    if result.get("success"):
                        return (result.get("output", ""), None)
                    else:
                        error_msg = result.get("error", "MCP tool execution failed")
                        return (f"Error: {error_msg}", None)
                else:
                    return (str(result), None)
            else:
                if isinstance(result, dict):
                    result_str = json.dumps(result, ensure_ascii=False, indent=2)
                else:
                    result_str = str(result)
                return (result_str, None)

        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            logger.error(f"Tool '{tool_name}' execution failed: {e}", exc_info=True)
            return (error_msg, None)

    def _create_thinking_step(
        self,
        step: int,
        tool_name: str,
        tool_args: Dict,
        tool_result: str,
        reasoning: Optional[str] = None,
    ) -> ThinkingStep:
        """Create a ThinkingStep object from tool execution.

        Args:
            step: Step number
            tool_name: Name of the tool
            tool_args: Tool arguments
            tool_result: Tool execution result
            reasoning: Optional GPT-5 reasoning

        Returns:
            ThinkingStep object
        """
        # Determine success
        is_error = (
            tool_result.startswith("Failed to")
            or tool_result.startswith("Tool execution failed")
            or (tool_result.startswith("Tool '") and "' not found" in tool_result)
        )

        urls = None
        has_code = False
        has_image = False

        if tool_name == "web_search":
            if "url" in tool_args:
                urls = [tool_args["url"]]
            elif "urls" in tool_args:
                urls = tool_args["urls"]
        elif tool_name == "execute_python":
            has_code = True
            if "image" in tool_result.lower() or "plot" in tool_result.lower():
                has_image = True

        return ThinkingStep(
            step=step,
            tool=tool_name,
            input=tool_args,
            output=tool_result,
            success=not is_error,
            thinking=reasoning,
            urls=urls,
            has_code=has_code,
            has_image=has_image,
        )

    def _cleanup_sandbox_only(self, tools: Dict):
        """Cleanup only e2b sandbox after each message.

        Args:
            tools: Dict of available tools
        """
        sandbox_tool = tools.get("execute_python")
        if sandbox_tool and hasattr(sandbox_tool, "cleanup"):
            try:
                sandbox_tool.cleanup()
            except Exception as e:
                logger.error(f"Failed to cleanup sandbox: {e}", exc_info=True)

    def get_chat_history(self) -> Dict:
        """Get current chat history for API response."""
        return self.chat_history
