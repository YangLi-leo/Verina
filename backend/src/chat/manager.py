"""Message manager for ReAct chatbot - handles conversation state."""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .model import MessageRole, MessageDisplay

logger = logging.getLogger(__name__)


class MessageManager:
    """Manage conversation messages for OpenRouter API.

    Handles all message types including tool calls and tool results.
    Automatically persists messages to disk when persist_dir is provided.
    """

    def __init__(self, system_prompt: str = "", persist_dir: Optional[Path] = None):
        """Initialize with optional system prompt and persistence.

        Args:
            system_prompt: Optional system prompt to add
            persist_dir: Optional directory for persisting messages to messages.json
        """
        self.messages: List[Dict[str, Any]] = []
        self.persist_dir = persist_dir
        self.messages_file = persist_dir / "messages.json" if persist_dir else None

        if self.messages_file and self.messages_file.exists():
            self._load()

        if system_prompt and not self.messages:
            self.add_system_message(system_prompt)

    def add_system_message(self, content: str) -> None:
        self.messages.append({
            "role": MessageRole.SYSTEM.value,
            "content": content
        })
        self._save()

    def add_user_message(self, content: str) -> None:
        self.messages.append({
            "role": MessageRole.USER.value,
            "content": content
        })
        self._save()

    def add_assistant_message(
        self,
        content: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Add assistant message. Supports GPT-5 style with both content and tool_calls.

        At least one of content or tool_calls must be provided.
        """
        message: Dict[str, Any] = {"role": MessageRole.ASSISTANT.value}

        if not content and not tool_calls:
            raise ValueError("Assistant message must have either content or tool_calls")

        message["content"] = content if content else None

        if tool_calls:
            for tc in tool_calls:
                assert "id" in tc, "Tool call missing 'id'"
                assert tc.get("type") == "function", "Tool call type must be 'function'"
                assert "function" in tc, "Tool call missing 'function'"
                assert "name" in tc["function"], "Tool call function missing 'name'"
                assert "arguments" in tc["function"], "Tool call function missing 'arguments'"

            message["tool_calls"] = tool_calls

        self.messages.append(message)
        self._save()

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        self.messages.append({
            "role": MessageRole.TOOL.value,
            "tool_call_id": tool_call_id,
            "content": content
        })
        self._save()

    def get_messages(self) -> List[Dict[str, Any]]:
        return self.messages

    def get_messages_for_frontend(self) -> List[MessageDisplay]:
        """Get messages formatted for frontend display.

        Filters out system messages and formats tool calls.
        """
        frontend_messages = []

        for msg in self.messages:
            role = msg.get("role")

            if role == MessageRole.SYSTEM.value:
                continue

            display_msg_dict = {
                "role": role,
                "content": msg.get("content", ""),
            }

            if "tool_calls" in msg:
                tool_names = [tc["function"]["name"] for tc in msg["tool_calls"]]
                display_msg_dict["tool_calls"] = tool_names
                if not display_msg_dict["content"]:
                    display_msg_dict["content"] = f"Using tools: {', '.join(tool_names)}"

            if "tool_call_id" in msg:
                display_msg_dict["is_tool_result"] = True

            frontend_messages.append(MessageDisplay(**display_msg_dict))

        return frontend_messages

    def clear(self, keep_system: bool = True) -> None:
        if keep_system:
            self.messages = [m for m in self.messages if m["role"] == MessageRole.SYSTEM.value]
        else:
            self.messages = []

    def get_last_message(self) -> Optional[Dict[str, Any]]:
        return self.messages[-1] if self.messages else None

    def get_conversation_length(self) -> int:
        """Return number of messages excluding system prompts."""
        return len([m for m in self.messages if m["role"] != MessageRole.SYSTEM.value])

    def _save(self) -> None:
        """Persist messages to disk."""
        if not self.messages_file:
            return

        try:
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self.messages_file.write_text(
                json.dumps(self.messages, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save messages: {e}")

    def _load(self) -> None:
        try:
            data = json.loads(self.messages_file.read_text(encoding="utf-8"))
            self.messages = data
            logger.info(f"Loaded {len(self.messages)} messages")
        except Exception as e:
            logger.error(f"Failed to load messages: {e}")