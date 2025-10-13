"""Agent Router - Routes between Chat Mode and Agent Mode.

This router manages mode switching, system prompt updates, and
maintains message history continuity across mode changes.
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Optional

from src.chat.config import ChatConfig
from src.chat.manager import MessageManager
from src.chat.prompts.prompt import CHAT_AGENT_SYSTEM_PROMPT, CHAT_MODE_PROMPT
from src.chat.agent.ChatModeAgent import ChatModeAgent
from src.chat.agent.AgentModeAgent import AgentModeAgent
from src.core.config import Config
from src.integrations.llm.openrouter import OpenRouterProvider

logger = logging.getLogger(__name__)


class AgentRouter:
    """
    Routes between Chat Mode and Agent Mode agents.

    Key responsibilities:
    - Manage shared MessageManager across modes
    - Handle mode switching with system prompt updates
    - Route requests to appropriate agent
    - Maintain conversation continuity
    """

    def __init__(
        self,
        llm_provider: Optional[OpenRouterProvider] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_iterations: int = None,
        session_id: Optional[str] = None,
        base_data_dir: Optional[Path] = None,
        chat_service: Optional[Any] = None,
    ):
        """Initialize Agent Router.

        Args:
            llm_provider: OpenRouter provider instance
            model: Model to use (for Agent Mode)
            temperature: Sampling temperature
            max_iterations: Maximum ReAct iterations
            session_id: Session identifier for file system workspace
            base_data_dir: Base directory for data storage
            chat_service: ChatService instance for cancellation support
        """
        self.llm_provider = llm_provider or OpenRouterProvider()
        self.model = model or ChatConfig.DEFAULT_MODEL
        self.temperature = temperature
        self.max_iterations = max_iterations or ChatConfig.MAX_ITERATIONS
        self.session_id = session_id
        self.chat_service = chat_service

        if session_id:
            data_base = base_data_dir if base_data_dir is not None else Path(Config.DATA_BASE_DIR).expanduser()
            self.search_base_dir = data_base / "chats" / session_id
            # MessageManager will save messages.json directly under chat directory
        else:
            self.search_base_dir = None

        self.chat_agent = ChatModeAgent(
            llm_provider=self.llm_provider,
            temperature=self.temperature,
            max_iterations=self.max_iterations,
            session_id=session_id,
            base_data_dir=base_data_dir,
            chat_service=chat_service,
        )

        self.agent_mode = AgentModeAgent(
            llm_provider=self.llm_provider,
            model=self.model,
            temperature=self.temperature,
            max_iterations=self.max_iterations,
            session_id=session_id,
            base_data_dir=base_data_dir,
            chat_service=chat_service,
        )

        # Shared message manager
        self.message_manager: Optional[MessageManager] = None

        # Track last mode for detecting switches
        self.last_mode: Optional[str] = None

        logger.info(f"AgentRouter initialized with session_id: {session_id}")

    def _handle_mode_switch(self, mode: str):
        """Handle mode switching logic including system prompt update.

        Args:
            mode: Target mode ("chat" or "agent")
        """
        if mode == self.last_mode:
            return  # No switch needed

        logger.info(f"[Mode Switch] Switching from {self.last_mode} to {mode}")

        current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if mode == "chat":
            new_prompt = CHAT_MODE_PROMPT.format(current_date=current_date)
        else:
            new_prompt = CHAT_AGENT_SYSTEM_PROMPT.format(current_date=current_date)

        if self.message_manager and self.message_manager.messages:
            self.message_manager.messages[0]["content"] = new_prompt
            logger.info(f"[Mode Switch] Updated system prompt for {mode} mode")

        # Reset Agent Mode to HIL stage when switching to agent
        if mode == "agent":
            self.agent_mode.reset_to_hil()
            logger.info("[Mode Switch] Reset Agent Mode to HIL stage")

    def _check_auto_reset_needed(self) -> bool:
        """Check if Agent Mode needs auto-reset from Research to HIL.

        Returns:
            True if reset is needed, False otherwise
        """
        if not self.message_manager:
            return False

        last_msg = self.message_manager.get_last_message()
        if last_msg and last_msg.get("role") == "assistant":
            content = last_msg.get("content", "")
            # Look for signs of research completion
            if "<!DOCTYPE html>" in content or "Research completed" in content:
                return True
        return False

    async def route_stream(
        self,
        message: str,
        user_id: str,
        session_id: str,
        system_prompt: Optional[str] = None,
        mode: str = "chat",
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Route to appropriate agent and stream responses.

        Args:
            message: User's message
            user_id: User identifier
            session_id: Session identifier
            system_prompt: Optional custom system prompt (for first message)
            mode: Operation mode - "chat" (default) or "agent"

        Yields:
            Events from the selected agent
        """
        current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if not self.message_manager:
            # First time initialization
            if mode == "chat":
                initial_prompt = CHAT_MODE_PROMPT.format(current_date=current_date)
            else:
                initial_prompt = system_prompt or CHAT_AGENT_SYSTEM_PROMPT.format(current_date=current_date)
            self.message_manager = MessageManager(initial_prompt, persist_dir=self.search_base_dir)
            self.last_mode = mode
            logger.info(f"[Init] MessageManager initialized with {mode} mode prompt")
        else:
            self._handle_mode_switch(mode)
            self.last_mode = mode

        # Auto-reset Agent Mode if needed
        if mode == "agent" and self.agent_mode.stage == "research":
            if self._check_auto_reset_needed():
                logger.info("[Agent] Auto-reset from Research to HIL after completion")
                self.agent_mode.reset_to_hil()

        # Route to appropriate agent
        if mode == "chat":
            logger.info(f"[Router] Routing to Chat Mode Agent")
            async for event in self.chat_agent.chat_stream(
                message=message,
                user_id=user_id,
                session_id=session_id,
                message_manager=self.message_manager,
            ):
                yield event
        else:
            logger.info(f"[Router] Routing to Agent Mode Agent (stage: {self.agent_mode.stage})")
            async for event in self.agent_mode.agent_stream(
                message=message,
                user_id=user_id,
                session_id=session_id,
                message_manager=self.message_manager,
            ):
                yield event

    def clear_conversation(self, keep_system: bool = True):
        """Clear conversation history.

        Args:
            keep_system: Whether to keep the system prompt
        """
        if self.message_manager:
            self.message_manager.clear(keep_system=keep_system)
        logger.info(f"Conversation cleared (keep_system={keep_system})")

    def cleanup(self):
        """Cleanup all resources."""
        # Cleanup both agents
        self.chat_agent.cleanup()
        self.agent_mode.cleanup()
        logger.info("AgentRouter cleanup completed")

    def get_chat_history(self) -> Dict:
        """Get chat history from the active agent.

        Since both agents share the same chat_history.json file,
        we can get it from either one.
        """
        # Prefer chat_agent as it's lighter weight
        if hasattr(self.chat_agent, 'get_chat_history'):
            return self.chat_agent.get_chat_history()
        elif hasattr(self.agent_mode, 'get_chat_history'):
            return self.agent_mode.get_chat_history()
        else:
            return {
                "session_id": self.session_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "responses": []
            }