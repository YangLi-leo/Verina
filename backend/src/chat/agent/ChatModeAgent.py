"""Chat Mode Agent - Quick responses with minimal tools.

This agent handles Chat Mode, providing fast responses with basic tools
like web_search, execute_python, and file_read for cached article access.

V2 Updates:
- Sources tracking for [1][2] citations
- chat_history.json persistence for frontend
- workspace_chat directory separation

V3 Updates:
- Refactored to inherit from BaseAgent to reduce code duplication
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Set

from src.chat.config import ChatConfig
from src.chat.manager import MessageManager
from src.chat.model import ChatResponse, ThinkingStep
from src.chat.tools.base import BaseTool
from src.chat.tools.execute_python import SandboxTool
from src.chat.tools.web_search import WebSearchTool
from src.chat.tools.file_read import FileReadTool
from src.chat.tools.mcp_tool import MCPTool
from src.chat.mcp_client import MCPClient
from src.integrations.llm.openrouter import OpenRouterProvider
from .BaseAgent import BaseAgent

logger = logging.getLogger(__name__)


class ChatModeAgent(BaseAgent):
    """
    Chat Mode agent for quick, direct responses.

    Features:
    - Lightweight tool set (web_search, execute_python, file_read)
    - Direct response generation
    - No stage progression
    - Uses Claude Sonnet for efficiency
    """

    def __init__(
        self,
        llm_provider: Optional[OpenRouterProvider] = None,
        temperature: float = 0.7,
        max_iterations: int = None,
        session_id: Optional[str] = None,
        base_data_dir: Optional[Path] = None,
        chat_service: Optional[Any] = None,
    ):
        """Initialize Chat Mode Agent.

        Args:
            llm_provider: OpenRouter provider instance
            temperature: Sampling temperature
            max_iterations: Maximum ReAct iterations
            session_id: Session identifier for file system workspace
            base_data_dir: Base directory for data storage
            chat_service: ChatService instance for cancellation support
        """
        super().__init__(
            llm_provider=llm_provider,
            model="anthropic/claude-sonnet-4.5",  # Fixed model for Chat Mode
            temperature=temperature,
            max_iterations=max_iterations,
            session_id=session_id,
            base_data_dir=base_data_dir,
            workspace_suffix="workspace_chat",
        )

        # Store chat_service reference for cancellation
        self.chat_service = chat_service

        if self.workspace_dir:
            self._initialize_workspace()

        self.tools: Dict[str, BaseTool] = {}
        self.mcp_client: Optional[MCPClient] = None

        # Note: _initialize_tools() is async now, will be called separately
        logger.info("ChatModeAgent created (MCP tools will be initialized on first use)")

    def _initialize_workspace(self):
        """Initialize workspace directory structure."""
        if not self.workspace_dir:
            return

        logger.info(f"Initializing workspace at {self.workspace_dir}")

        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        (self.workspace_dir / "cache").mkdir(exist_ok=True)
        (self.workspace_dir / "analysis" / "images").mkdir(parents=True, exist_ok=True)
        (self.workspace_dir / "analysis" / "data").mkdir(parents=True, exist_ok=True)

    async def _initialize_tools(self):
        """Initialize Chat Mode tools (including MCP tools)."""
        from src.core.config import Config

        # Core tools
        web_search_tool = WebSearchTool(workspace_dir=self.workspace_dir)

        self.tools = {
            web_search_tool.name: web_search_tool,
        }

        # Add SandboxTool only if E2B_API_KEY is configured
        if Config.has_e2b_key():
            sandbox_tool = SandboxTool(workspace_dir=self.workspace_dir)
            self.tools[sandbox_tool.name] = sandbox_tool
            logger.info("✓ SandboxTool (execute_python) enabled - E2B_API_KEY configured")
        else:
            logger.info("⚠ SandboxTool (execute_python) disabled - E2B_API_KEY not configured")

        if self.workspace_dir:
            file_read_tool = FileReadTool(workspace_dir=self.workspace_dir)
            self.tools[file_read_tool.name] = file_read_tool

        # Initialize MCP client and tools
        try:
            logger.info("Initializing MCP client...")
            self.mcp_client = MCPClient()

            # Connect to all MCP servers
            tools_by_server = await self.mcp_client.connect_all_servers()

            # Wrap each MCP tool and add to self.tools
            mcp_tool_count = 0
            for server_name, server_tools in tools_by_server.items():
                for tool_info in server_tools:
                    # Create wrapper
                    mcp_tool = MCPTool(
                        mcp_client=self.mcp_client,
                        server_name=server_name,
                        tool_name=tool_info.name,
                        description=tool_info.description or "",
                        input_schema=tool_info.inputSchema if hasattr(tool_info, 'inputSchema') else {}
                    )

                    # Add to tools dict with MCP prefix
                    self.tools[mcp_tool.name] = mcp_tool
                    mcp_tool_count += 1

            logger.info(f"✓ MCP tools initialized: {mcp_tool_count} tools from {len(tools_by_server)} servers")

        except Exception as e:
            logger.warning(f"Failed to initialize MCP tools: {e}")
            logger.info("Continuing without MCP tools...")

        logger.info(f"Initialized Chat Mode tools: {list(self.tools.keys())}")

    def _get_tools_for_openrouter(self) -> List[Dict[str, Any]]:
        """Get tools in OpenRouter format."""
        return [tool.to_openrouter_format() for tool in self.tools.values()]

    async def chat_stream(
        self,
        message: str,
        user_id: str,
        session_id: str,
        message_manager: MessageManager,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream chat with ReAct loop and sources tracking.

        Args:
            message: User's message
            user_id: User identifier
            session_id: Session identifier (actually search_id)
            message_manager: Message manager for conversation history

        Yields:
            - {"type": "thinking_step", "data": ThinkingStep} - tool execution results
            - {"type": "complete", "data": ChatResponse with sources} - at the end
        """
        # Initialize tools on first use (lazy initialization for MCP)
        if not self.tools:
            await self._initialize_tools()

        start_time = time.time()
        thinking_steps: List[ThinkingStep] = []
        tools_used_set: Set[str] = set()
        step_counter = 0
        last_prompt_tokens = 0

        # Reset current sources for new response
        self.current_sources = []

        logger.info(f"[Chat Mode] Processing message with sources tracking")

        message_manager.add_user_message(message)

        # ReAct Loop
        iteration = 0
        final_response = ""

        try:
            while iteration < self.max_iterations:
                iteration += 1
                logger.info(f"[Chat Mode] Iteration {iteration}/{self.max_iterations}")

                # Check for cancellation
                if self.chat_service and self.chat_service.cancel_flags.get(session_id):
                    logger.info(f"[Chat Mode] Cancelled by user at iteration {iteration}")

                    # Clean workspace on cancellation
                    if self.workspace_dir and self.workspace_dir.exists():
                        logger.info("[Chat Cancellation] Cleaning workspace")
                        self._clean_workspace_after_chat()

                    final_response = "Response stopped by user."

                    # Clear the cancel flag
                    self.chat_service.clear_cancel_flag(session_id)

                    # Yield cancellation event
                    yield {
                        "type": "cancelled",
                        "message": "Stopped by user",
                        "steps_completed": len(thinking_steps)
                    }

                    break  # Exit loop

                response = await self.llm_provider.chat(
                    messages=message_manager.get_messages(),
                    model=self.model,
                    temperature=self.temperature,
                    tools=self._get_tools_for_openrouter(),
                    tool_choice="auto",
                )

                # Track usage
                if "usage" in response:
                    usage = response["usage"]
                    last_prompt_tokens = usage.get("prompt_tokens", 0)
                    total_tokens = usage.get("total_tokens", 0)
                    logger.info(f"[Chat Mode] Context: {last_prompt_tokens} tokens | Total: {total_tokens}")

                message_data = response["choices"][0]["message"]
                content = message_data.get("content", "")
                tool_calls = message_data.get("tool_calls")

                # Check if LLM wants to use tools
                if tool_calls:
                    message_manager.add_assistant_message(
                        content=content if content else None,
                        tool_calls=tool_calls
                    )

                    for tool_call in tool_calls:
                        step_counter += 1
                        tool_name = tool_call["function"]["name"]
                        tool_args_str = tool_call["function"]["arguments"]

                        try:
                            tool_args = json.loads(tool_args_str)
                        except json.JSONDecodeError:
                            tool_args = {"raw": tool_args_str}

                        tools_used_set.add(tool_name)

                        tool_result, _ = await self._execute_tool(tool_call, self.tools)

                        # If web_search returned sources, they're already in self.current_sources

                        thinking_step = self._create_thinking_step(
                            step=step_counter,
                            tool_name=tool_name,
                            tool_args=tool_args,
                            tool_result=tool_result,
                        )
                        thinking_steps.append(thinking_step)

                        # Yield thinking step to frontend
                        yield {"type": "thinking_step", "data": thinking_step.model_dump(mode='json')}

                        message_manager.add_tool_result(
                            tool_call_id=tool_call["id"], content=tool_result
                        )

                    # Continue loop for next iteration
                    continue

                else:
                    # No tool calls - content is the final answer
                    logger.info(f"[Chat Mode] Final answer ready ({len(content)} chars)")
                    final_response = content if content else "I don't have a response at this time."

                    message_manager.add_assistant_message(content=final_response)

                    # Break loop
                    break

        except Exception as e:
            logger.error(f"[Chat Mode] Error: {e}", exc_info=True)
            error_msg = f"Error during processing: {str(e)}"
            message_manager.add_assistant_message(content=error_msg)
            yield {"type": "error", "data": error_msg}
            return

        finally:
            # Cleanup sandbox
            self._cleanup_sandbox_only(self.tools)

        total_time_ms = int((time.time() - start_time) * 1000)

        # Determine characteristics
        has_code = any(step.has_code for step in thinking_steps)
        has_web_results = any(step.tool == "web_search" for step in thinking_steps)

        # Add to chat history and get response_id
        response_id = self._add_response_to_history(
            user_message=message,
            assistant_message=final_response,
            sources=self.current_sources,
            thinking_steps=thinking_steps if thinking_steps else None,
            total_time_ms=total_time_ms,
            mode="chat",
            prompt_tokens=last_prompt_tokens if last_prompt_tokens > 0 else None,
        )

        chat_response = ChatResponse(
            response_id=response_id,
            session_id=session_id,
            user_id=user_id,
            user_message=message,
            assistant_message=final_response,
            thinking_steps=thinking_steps if thinking_steps else None,
            sources=self.current_sources if self.current_sources else None,  # Add sources for frontend
            mode="chat",  # Indicate this is from chat mode
            used_tools=len(thinking_steps) > 0,
            has_code=has_code,
            has_web_results=has_web_results,
            total_time_ms=total_time_ms,
            model_used=self.model,
            temperature=self.temperature,
            prompt_tokens=last_prompt_tokens if last_prompt_tokens > 0 else None,
        )

        # Clean workspace after chat completion
        if self.workspace_dir and self.workspace_dir.exists():
            self._clean_workspace_after_chat()

        # Yield complete signal
        yield {"type": "complete", "data": chat_response.model_dump(mode='json')}

    def _clean_workspace_after_chat(self):
        """Clean workspace directory after chat completion.

        This removes all temporary files from the chat session:
        - cache/ (downloaded articles)
        - analysis/ (Python execution outputs)

        The workspace will be recreated fresh for the next chat session.
        """
        import shutil

        try:
            if self.workspace_dir and self.workspace_dir.exists():
                logger.info(f"[Cleanup] Removing workspace after chat completion: {self.workspace_dir}")
                shutil.rmtree(self.workspace_dir)
                logger.info("[Cleanup] Workspace cleaned successfully")
        except Exception as e:
            logger.error(f"[Cleanup] Failed to clean workspace: {e}", exc_info=True)

    def cleanup(self):
        """Cleanup all resources including MCP connections."""
        # Cleanup tools
        for tool_name, tool in self.tools.items():
            if hasattr(tool, "cleanup"):
                try:
                    tool.cleanup()
                except Exception as e:
                    logger.error(f"Failed to cleanup tool '{tool_name}': {e}", exc_info=True)

        # Cleanup MCP connections
        if self.mcp_client:
            try:
                import asyncio
                # Try to get current event loop
                try:
                    loop = asyncio.get_running_loop()
                    # Loop is running - log warning as we can't cleanup synchronously
                    logger.warning("MCP cleanup skipped - event loop is running. "
                                 "MCP connections will be cleaned up on process exit.")
                except RuntimeError:
                    # No running loop - safe to run cleanup
                    asyncio.run(self.mcp_client.cleanup())
            except Exception as e:
                logger.error(f"Failed to cleanup MCP client: {e}", exc_info=True)