"""Chat Service - API adapter for AgentRouter (matches SearchService pattern)."""

import json
import logging
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.chat import AgentRouter, ChatResponse
from src.core.config import Config
from src.integrations.llm.openrouter import OpenRouterProvider

logger = logging.getLogger(__name__)


class ChatService:
    """Chat service - Direct adapter for AgentRouter with session management.

    Architecture (matching SearchService):
    - Manages session lifecycle (create/retrieve AgentRouter instances)
    - Routes between Chat Mode and Agent Mode
    - Handles history and persistence
    """

    def __init__(self):
        """Initialize chat service with dependencies."""
        self.llm_provider = OpenRouterProvider()

        self.routers: Dict[str, AgentRouter] = {}

        self.base_dir = Path(Config.DATA_BASE_DIR).expanduser()

        self.chat_records: Dict[str, Dict[str, Any]] = {}

        self.cancel_flags: Dict[str, bool] = {}

        self._load_existing_sessions()

        logger.info("ChatService initialized")

    def _load_existing_sessions(self):
        """Load all existing chat sessions from file system on startup.

        Scans /app/data/chats/ directory and populates self.chat_records
        so that history API returns all sessions even after server restart.
        """
        try:
            chats_dir = self.base_dir / "chats"

            if not chats_dir.exists():
                logger.info("No chats directory found, starting fresh")
                return

            loaded_count = 0

            for session_dir in chats_dir.iterdir():
                if not session_dir.is_dir():
                    continue

                session_id = session_dir.name
                chat_history_file = session_dir / "chat_history.json"

                if not chat_history_file.exists():
                    logger.debug(f"Skipping {session_id} - no chat_history.json")
                    continue

                try:
                    with open(chat_history_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    responses = data.get("responses", [])
                    if not responses:
                        logger.debug(f"Skipping {session_id} - empty responses")
                        continue

                    first_response = responses[0]
                    user_id = first_response.get("user_id", "anonymous")
                    user_message = first_response.get("user_message", "")

                    created_at = data.get("created_at")
                    updated_at = data.get("updated_at")

                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if isinstance(updated_at, str):
                        updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))

                    self.chat_records[session_id] = {
                        "session_id": session_id,
                        "user_id": user_id,
                        "first_message": user_message[:100],  # First 100 chars
                        "display_name": None,  # Will be generated on demand if needed
                        "message_count": len(responses),
                        "created_at": created_at,
                        "updated_at": updated_at,
                    }

                    loaded_count += 1

                except Exception as e:
                    logger.error(f"Failed to load session {session_id}: {e}")
                    continue

            logger.info(f"Loaded {loaded_count} existing chat sessions from file system")

        except Exception as e:
            logger.error(f"Failed to load existing sessions: {e}", exc_info=True)

    def _get_or_create_router(self, session_id: str) -> AgentRouter:
        """Get existing AgentRouter for session or create new one.

        Args:
            session_id: Session identifier

        Returns:
            AgentRouter instance for this session
        """
        if session_id not in self.routers:
            logger.info(f"Creating new AgentRouter for session {session_id}")
            self.routers[session_id] = AgentRouter(
                llm_provider=self.llm_provider,
                session_id=session_id,
                base_data_dir=self.base_dir,  # Pass unified base directory
                chat_service=self,  # Pass self for cancellation support
            )
        return self.routers[session_id]

    async def process_message_stream(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: str = "anonymous",
        mode: str = "chat",
    ):
        """Process a chat message and stream events (thinking steps + answer chunks).

        This is the streaming version that yields events in real-time.

        Args:
            message: User's message
            session_id: Optional - will be auto-generated if not provided
            user_id: User identifier
            mode: Operation mode - "chat" or "agent"

        Yields:
            Events: thinking_step, stage_switch, complete, error
        """
        try:
            if not session_id:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                random_suffix = secrets.token_hex(4)
                session_id = f"chat_{timestamp}_{random_suffix}"
                logger.info(f"Auto-generated session_id: {session_id}")

                yield {"type": "session_created", "session_id": session_id}

            router = self._get_or_create_router(session_id)

            final_response = None
            async for event in router.route_stream(
                message=message,
                user_id=user_id,
                session_id=session_id,
                mode=mode,
            ):
                yield event

                if event.get("type") == "complete":
                    final_response = event.get("data")

            if final_response:
                from src.chat.model import ChatResponse
                chat_response = ChatResponse(**final_response)
                await self._save_chat_record(session_id, user_id, message, chat_response)

        except Exception as e:
            logger.error(f"Process message stream error: {e}", exc_info=True)
            yield {"type": "error", "message": str(e)}

    async def process_message(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_id: str = "anonymous",
        mode: str = "chat",
    ) -> ChatResponse:
        """Process a chat message and return complete response (non-streaming).

        This is a convenience wrapper around process_message_stream() for non-streaming use.

        Args:
            message: User's message
            session_id: Optional session ID (will be generated if not provided)
            user_id: User identifier

        Returns:
            ChatResponse for frontend
        """
        try:
            final_response = None

            async for event in self.process_message_stream(
                message=message,
                session_id=session_id,
                user_id=user_id,
                mode=mode,
            ):
                if event.get("type") == "complete":
                    final_response = event.get("data")

            if not final_response:
                raise RuntimeError("Stream did not produce a complete response")

            from src.chat.model import ChatResponse
            return ChatResponse(**final_response)

        except Exception as e:
            logger.error(f"Process message error: {e}", exc_info=True)
            raise

    async def get_conversation_history(
        self, session_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get full conversation history for a session.

        Args:
            session_id: Session identifier
            user_id: User identifier for access control

        Returns:
            Conversation history with all messages
        """
        router = self.routers.get(session_id)
        if not router:
            return None

        record = self.chat_records.get(session_id)
        if not record or record.get("user_id") != user_id:
            return None

        chat_history = router.get_chat_history()

        return {
            "session_id": session_id,
            "responses": chat_history.get("responses", []),
            "total_messages": len(chat_history.get("responses", [])),
            "created_at": chat_history.get("created_at"),
            "updated_at": chat_history.get("updated_at"),
        }

    async def get_conversation_history_public(
        self, session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get conversation history without user verification (public access via session_id).

        Returns complete ChatResponse list with thinking_steps and artifact for full state restoration.

        Args:
            session_id: Session identifier (acts as access token)

        Returns:
            {
                "session_id": str,
                "responses": List[ChatResponse],  # Complete responses with thinking_steps + artifact + sources
                "total_messages": int
            }
        """
        try:
            chat_history_file = self.base_dir / "chats" / session_id / "chat_history.json"

            if not chat_history_file.exists():
                logger.warning(f"No chat history found for session {session_id}")
                return None

            with open(chat_history_file, 'r', encoding='utf-8') as f:
                chat_history = json.load(f)

            responses = chat_history.get("responses", [])
            if not responses:
                return None

            logger.info(f"Loaded {len(responses)} ChatResponses from {chat_history_file}")
            return {
                "session_id": session_id,
                "responses": responses,  # Complete ChatResponse objects with thinking_steps + sources
                "total_messages": len(responses),
                "created_at": chat_history.get("created_at"),
                "updated_at": chat_history.get("updated_at"),
            }

        except Exception as e:
            logger.error(f"Failed to load conversation history: {e}", exc_info=True)
            return None

    async def get_user_chat_sessions(
        self, user_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get user's chat sessions for history sidebar.

        Args:
            user_id: User identifier
            limit: Maximum number of sessions to return

        Returns:
            List of session summaries
        """
        user_sessions = []

        for session_id, record in self.chat_records.items():
            if record.get("user_id") == user_id:
                user_sessions.append({
                    "session_id": session_id,
                    "first_message": record.get("first_message", ""),
                    "display_name": record.get("display_name"),  # LLM-generated title
                    "message_count": record.get("message_count", 0),
                    "created_at": record.get("created_at"),
                    "updated_at": record.get("updated_at"),
                })

        user_sessions.sort(
            key=lambda x: x.get("updated_at", datetime.min), reverse=True
        )

        return user_sessions[:limit]

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a chat session.

        Args:
            session_id: Session identifier
            user_id: User identifier for access control

        Returns:
            True if deleted, False if not found or unauthorized
        """
        record = self.chat_records.get(session_id)
        if not record or record.get("user_id") != user_id:
            return False

        router = self.routers.get(session_id)
        if router:
            router.cleanup()  # Cleanup both agents
            del self.routers[session_id]

        del self.chat_records[session_id]

        logger.info(f"Deleted session {session_id}")
        return True

    async def clear_session_conversation(self, session_id: str, user_id: str) -> bool:
        """Clear conversation history but keep session alive.

        Args:
            session_id: Session identifier
            user_id: User identifier for access control

        Returns:
            True if cleared, False if not found or unauthorized
        """
        record = self.chat_records.get(session_id)
        if not record or record.get("user_id") != user_id:
            return False

        router = self.routers.get(session_id)
        if router:
            router.clear_conversation(keep_system=True)  # Keeps system prompt

        record["message_count"] = 0
        record["updated_at"] = datetime.now(timezone.utc)

        return True

    async def _generate_display_name(self, user_message: str, assistant_preview: str = "") -> str:
        """Generate a concise display name for chat history using LLM.

        Args:
            user_message: User's first message
            assistant_preview: Optional preview of assistant's response (first 200 chars)

        Returns:
            Concise 10-20 word title for history display
        """
        try:
            prompt = f"""Generate a concise, clear title (10-20 words) for this chat conversation.
The title should capture the main topic or question being discussed.

User's first message: {user_message}
{f'Assistant preview: {assistant_preview[:200]}...' if assistant_preview else ''}

Requirements:
- 10-20 words
- Clear and descriptive
- No quotes or special formatting
- Capitalize like a title

Title:"""

            response = await self.llm_provider.chat(
                messages=[{"role": "user", "content": prompt}],
                model="openai/gpt-5-chat",
                temperature=0.3,  # Lower temperature for consistent titles
                max_tokens=60,  # Enough for 10-20 words
            )

            # Extract content from OpenRouter response format
            display_name = response.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

            if not display_name or len(display_name) < 3:
                display_name = user_message[:80] + ("..." if len(user_message) > 80 else "")

            logger.info(f"Generated display_name for chat: '{display_name}' from message: '{user_message[:50]}'")
            return display_name

        except Exception as e:
            logger.error(f"Failed to generate display_name for chat: {e}")
            return user_message[:80] + ("..." if len(user_message) > 80 else "")

    async def _save_chat_record(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        response: ChatResponse,
    ):
        """Save chat record to in-memory storage (chat_history.json handled by AgentRouter).

        Args:
            session_id: Session identifier
            user_id: User identifier
            user_message: User's message
            response: ChatResponse with complete data (thinking_steps, sources, artifact, etc.)
        """
        try:
            if session_id not in self.chat_records:
                display_name = await self._generate_display_name(
                    user_message=user_message,
                    assistant_preview=response.assistant_message[:200] if response.assistant_message else ""
                )

                self.chat_records[session_id] = {
                    "session_id": session_id,
                    "user_id": user_id,
                    "first_message": user_message[:100],  # First 100 chars for display
                    "display_name": display_name,  # LLM-generated title
                    "message_count": 1,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
            else:
                self.chat_records[session_id]["message_count"] += 1
                self.chat_records[session_id]["updated_at"] = datetime.now(timezone.utc)

            logger.info(f"Saved chat record for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to save chat record: {e}")

    def cancel_session(self, session_id: str):
        """Set cancellation flag for a session (called when user clicks stop button).

        Args:
            session_id: Session identifier to cancel
        """
        self.cancel_flags[session_id] = True
        logger.info(f"[Cancellation] Flag set for session {session_id}")

    def clear_cancel_flag(self, session_id: str):
        """Clear cancellation flag after handling.

        Args:
            session_id: Session identifier to clear
        """
        if session_id in self.cancel_flags:
            del self.cancel_flags[session_id]
            logger.info(f"[Cancellation] Flag cleared for session {session_id}")

    async def close(self):
        """Clean up resources."""
        for session_id, router in self.routers.items():
            try:
                router.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up router {session_id}: {e}")

        if hasattr(self.llm_provider, "close"):
            await self.llm_provider.close()

        logger.info("ChatService closed")