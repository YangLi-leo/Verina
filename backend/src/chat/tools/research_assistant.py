"""Research Assistant Tool - Auxiliary agent with multi-turn conversation support.

This tool invokes a separate LLM agent that:
1. Maintains its own conversation history (conv_id based)
2. Can read workspace files to save main LLM's context
3. Provides strategic guidance through multi-turn dialogue
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from .base import BaseTool
from .file_read import FileReadTool
from src.chat.manager import MessageManager

logger = logging.getLogger(__name__)


class ResearchAssistantTool(BaseTool):
    """Auxiliary research assistant with conversation memory.

    **Purpose:**
    - Save main LLM's context by delegating file reading/analysis
    - Multi-turn consultation like chatting with a colleague
    - Strategic guidance (research direction, draft review, etc.)

    **Conversation Management:**
    - Each conv_id = independent conversation thread
    - Stored in workspace/conversations/{conv_id}/messages.json
    - Must provide conv_id to continue previous conversation
    - No conv_id = new conversation created

    **Example Workflow:**
    1. Main LLM: "Analyze cache/article.md on quantum computing"
       → Assistant reads file, returns summary + conv_id="conv_001"
    2. Main LLM: "What about qubit stability?", conv_id="conv_001"
       → Continues conversation, remembers context
    3. Main LLM: "Review my draft.md", conv_id="conv_002"
       → New conversation for draft review
    """

    def __init__(self, llm_provider, workspace_dir: Optional[Path] = None):
        """Initialize research assistant.

        Args:
            llm_provider: LLM provider for assistant agent
            workspace_dir: Workspace directory for file access
        """
        self.llm_provider = llm_provider
        self.workspace_dir = workspace_dir
        self.conversations_dir = workspace_dir / "conversations" if workspace_dir else None

        if self.conversations_dir:
            self.conversations_dir.mkdir(parents=True, exist_ok=True)

        self.system_prompt = """You are a friendly research buddy - think of yourself as a helpful colleague who's here to chat and collaborate.

**You're here to help with:**
- Reading and analyzing files from the workspace
- Giving second opinions on research direction
- Answering questions about content you've read
- Reviewing drafts and providing feedback

**Available tools:**
- file_read: Read workspace files (progress.md, notes.md, draft.md, cache/*.md, etc.)

**How to interact:**
- Be conversational and approachable - no formality needed
- When asked about a file, just read it with file_read
- Give honest, helpful feedback
- Remember our conversation as we go
- Don't hesitate to ask clarifying questions if something's unclear

Remember: You're a collaborator, not a servant. Feel free to push back, ask questions, or suggest alternatives. The goal is to have a natural back-and-forth conversation about the research.
"""

    @property
    def name(self) -> str:
        return "research_assistant"

    @property
    def description(self) -> str:
        return (
            "Chat with a friendly research buddy who can read and analyze workspace files for you. "
            "Great for: getting a second opinion on articles, comparing multiple sources, reviewing your drafts, "
            "or just bouncing ideas around. The buddy remembers your conversation (via conv_id), "
            "so you can have a natural back-and-forth discussion. No need to be formal - just ask like you'd ask a colleague!"
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": (
                        "Your question or request for the research assistant. "
                        "Can ask to read files, analyze content, provide guidance, review work, etc."
                    )
                },
                "conv_id": {
                    "type": "string",
                    "description": (
                        "Conversation ID to continue previous dialogue. "
                        "Omit to start new conversation. "
                        "Returns conv_id in response for subsequent calls."
                    )
                }
            },
            "required": ["question"]
        }

    async def execute(self, question: str, conv_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute research assistant consultation.

        Args:
            question: Question or request for the assistant
            conv_id: Optional conversation ID to continue previous dialogue

        Returns:
            Dict with:
            - success: bool
            - answer: Assistant's response
            - conv_id: Conversation ID for follow-up
            - total_messages: Number of messages in conversation
        """
        try:
            if conv_id:
                conv_dir = self.conversations_dir / conv_id
                if not conv_dir.exists() or not (conv_dir / "messages.json").exists():
                    return {
                        "success": False,
                        "error": f"Conversation {conv_id} not found. Omit conv_id to start new conversation.",
                        "answer": ""
                    }
                message_manager = MessageManager(persist_dir=conv_dir)
                logger.info(f"Continuing conversation {conv_id}: {message_manager.get_conversation_length()} messages")
            else:
                conv_id = f"conv_{uuid4().hex[:8]}"
                conv_dir = self.conversations_dir / conv_id
                conv_dir.mkdir(parents=True, exist_ok=True)
                message_manager = MessageManager(
                    system_prompt=self.system_prompt,
                    persist_dir=conv_dir
                )
                logger.info(f"Created new conversation {conv_id}")

            message_manager.add_user_message(question)

            file_read_tool = None
            if self.workspace_dir:
                file_read_tool = FileReadTool(workspace_dir=self.workspace_dir)

            max_iterations = 10
            final_answer = None

            for iteration in range(max_iterations):
                logger.info(f"Assistant iteration {iteration + 1}/{max_iterations}")

                tools = [file_read_tool.to_openrouter_format()] if file_read_tool else None

                response = await self.llm_provider.chat(
                    messages=message_manager.get_messages(),
                    tools=tools,
                    temperature=0.7,
                    model="openai/gpt-5",
                )

                assistant_msg = response.get("choices", [{}])[0].get("message", {})
                reasoning = assistant_msg.get("reasoning", "")
                content = assistant_msg.get("content")
                tool_calls = assistant_msg.get("tool_calls", [])

                if not tool_calls:
                    message_manager.add_assistant_message(content=content)
                    final_answer = content
                    logger.info(f"Assistant finished after {iteration + 1} iterations")
                    break


                message_manager.add_assistant_message(content=reasoning if reasoning else content, tool_calls=tool_calls)

                logger.info(f"Assistant calling {len(tool_calls)} tools")
                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    tool_args = json.loads(tool_call["function"]["arguments"])
                    tool_call_id = tool_call["id"]

                    if tool_name == "file_read":
                        result = await file_read_tool.execute(**tool_args)
                        result_str = json.dumps(result, ensure_ascii=False)
                        logger.info(f"file_read({tool_args.get('filename')}) → {result.get('success')}")
                    else:
                        result_str = json.dumps({"error": f"Unknown tool: {tool_name}"})

                    message_manager.add_tool_result(tool_call_id, result_str)

            if not final_answer:
                logger.error("Assistant exceeded max iterations without answer")
                return {
                    "success": False,
                    "error": "Assistant timeout",
                    "answer": "",
                    "conv_id": conv_id
                }

            return {
                "success": True,
                "answer": final_answer,
                "conv_id": conv_id,
                "total_messages": message_manager.get_conversation_length() + 1  # +1 for system message
            }

        except Exception as e:
            error_msg = f"Research assistant error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "answer": "Unable to consult research assistant at this time."
            }
