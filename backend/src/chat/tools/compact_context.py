"""Tool to compact conversation context when token limit is reached.

This tool operates as a mini-agent that:
1. Reads workspace files (progress.md, notes.md, draft.md) to understand current state
2. Reviews old messages to understand conversation history
3. Generates a structured summary that preserves critical information
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseTool
from .file_read import FileReadTool
from src.chat.manager import MessageManager
from src.chat.model import MessageRole

logger = logging.getLogger(__name__)


# Compaction agent system prompt - autonomous tool-calling agent
COMPACTION_AGENT_SYSTEM_PROMPT = """You are a conversation context compressor agent. Your job: compress old conversation history into a structured summary that allows the main agent to resume seamlessly.

<your_task>
You will be given old conversation messages to compress. Your goal is to extract and organize critical information into 5 structured sections using XML tags.

You can use tools to help you understand the context better (e.g., read workspace files to see what's been created).
</your_task>

<available_tools>
You have ONE tool available: file_read

**file_read(filename: str)**
- Reads a file from the workspace
- Parameter: filename - relative path to the file (e.g., "progress.md", "cache/article_name.md")
- Returns: File content as text

**When to use file_read**:
- You see file paths mentioned in the conversation
- You need to understand what's in progress.md, notes.md, or draft.md
- You want to check cached articles to better summarize findings

**ReAct workflow**:
1. Review conversation messages
2. If you need more context → call file_read tool(s)
3. After tool results, go back to step 1
4. When you have enough information → output your final answer

**Final answer**:
When you're ready to provide the summary, simply output your answer directly (without calling any tools):
- First: <scratchpad> with your analysis
- Then: 5 XML sections (overall_goal, file_system_state, key_knowledge, recent_actions, current_plan)

The absence of tool calls signals you're providing the final result.
</available_tools>

<thinking_process>
Before generating the final summary, use a private scratchpad to organize your thoughts:

1. **Scratchpad (private thinking space)**:
   - Wrap your analysis in <scratchpad>...</scratchpad>
   - Review the entire conversation history
   - Identify: user's goal, agent's strategy, tool outputs, file changes, unresolved issues
   - This is for YOUR thinking - be thorough and honest
   - Note: "private" means you can think freely without worrying about format

2. **Final Summary**:
   - After scratchpad, output the structured 5-section summary
   - The summary is what the main agent will see
</thinking_process>

<output_format>
Your complete output should be:

<scratchpad>
[Your private analysis here - review history, identify patterns, note key information]
</scratchpad>

Then output exactly 5 XML sections:

<overall_goal>
Extract from user's initial request. One clear sentence. What is the ultimate objective?
Example: "Compare top 5 production LLMs on cost, performance, and streaming support for $500/month budget"
</overall_goal>

<file_system_state>
ALL file operations with CREATED/MODIFIED/READ prefixes. Include what each file contains and navigation hints.
Format:
- CREATED: cache/article.md - Brief description of content
- MODIFIED: notes.md - What changed
- READ: progress.md - Key discovery from reading
- HINT: Where to find specific information
- STATUS: Overall workspace state
Preserve exact file paths. Map information locations.
</file_system_state>

<key_knowledge>
Hard facts, research insights, reasoning takeaways:
- Specific data points with numbers and units
- URLs, API endpoints, technical specs
- Discoveries and patterns
- Constraints and requirements
- Strategic decisions made and why
Focus on facts that affect next steps.
</key_knowledge>

<recent_actions>
Last 5-10 tool executions with FULL DETAILS:
- tool_name(exact_parameters) → specific_result
- Include: file paths, data extracted, errors
- Be comprehensive: agent resumes from here
</recent_actions>

<current_plan>
Next immediate steps and continuation strategy:
- Numbered action items
- Pending decisions or questions
- Overall strategy for continuation
</current_plan>
</output_format>

<critical_rules>
1. Use file_read if you need context, but not all files may be needed
2. Focus on FACTS and RESULTS in the conversation, not process descriptions
3. Be comprehensive in recent_actions - include full tool parameters and results
4. Preserve ALL file paths exactly as mentioned
5. Include specific numbers, URLs, data points
6. When ready to summarize: output final answer WITHOUT calling any tools
</critical_rules>

You are autonomous - decide what information you need and how to extract it."""


# User prompt template for providing conversation history
COMPACTION_HISTORY_TEMPLATE = """Based on the workspace files you've reviewed, now summarize the following conversation history:

{messages_text}

Generate a structured summary following the format specified in your system prompt."""


class CompactContextTool(BaseTool):
    """Compact conversation context to reduce token usage.

    Strategy:
    - Keep system message and recent 10 user messages (with their responses) intact
    - Summarize older messages using LLM
    - Replace old messages with summary
    """

    def __init__(
        self,
        message_manager: MessageManager = None,
        llm_provider=None,
        workspace_dir: Optional[Path] = None
    ):
        """Initialize compact context tool.

        Args:
            message_manager: MessageManager instance (injected at runtime)
            llm_provider: LLM provider for summarization
            workspace_dir: Path to workspace directory (for reading context files)
        """
        self.message_manager = message_manager
        self.llm_provider = llm_provider
        self.workspace_dir = workspace_dir

    @property
    def name(self) -> str:
        return "compact_context"

    @property
    def description(self) -> str:
        return (
            "Compact conversation context to reduce token usage. "
            "Summarizes older messages while preserving recent 10 user turns intact. "
            "Use when experiencing reasoning difficulties or approaching context limits. "
            "System auto-compacts at 280k tokens if not called earlier."
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "keep_recent_user_messages": {
                    "type": "integer",
                    "description": "Number of recent user messages to keep intact (default: 10)",
                    "default": 10
                }
            },
            "required": []
        }

    async def execute(self, keep_recent_user_messages: int = 10) -> Dict[str, Any]:
        """Compact conversation context.

        Args:
            keep_recent_user_messages: Number of recent user messages to preserve (default: 10)

        Returns:
            Dict with compaction results
        """
        if not self.message_manager:
            logger.error("MessageManager not injected")
            return {"success": False, "error": "MessageManager not available"}

        if not self.llm_provider:
            logger.error("LLM provider not available")
            return {"success": False, "error": "LLM provider not available"}

        try:
            # 1. Get all messages
            all_messages = self.message_manager.get_messages()

            if len(all_messages) <= 3:
                return {
                    "success": True,
                    "message": "Too few messages to compact",
                    "messages_before": len(all_messages),
                    "messages_after": len(all_messages)
                }

            # 2. Find system messages
            system_messages = [m for m in all_messages if m["role"] == MessageRole.SYSTEM.value]

            # 3. Find the position of the 10th user message from the end
            user_count = 0
            split_index = len(all_messages)  # Default: keep everything

            for i in range(len(all_messages) - 1, -1, -1):
                if all_messages[i]["role"] == MessageRole.USER.value:
                    user_count += 1
                    if user_count == keep_recent_user_messages:
                        split_index = i
                        break

            # If we found less than 10 user messages, nothing to compact
            if user_count < keep_recent_user_messages:
                return {
                    "success": True,
                    "message": f"Only {user_count} user messages found, keeping all",
                    "messages_before": len(all_messages),
                    "messages_after": len(all_messages)
                }

            # 4. Split messages
            # old_messages: from after system to split_index (not including split_index)
            # recent_messages: from split_index to end
            system_end = len(system_messages)
            old_messages = all_messages[system_end:split_index]
            recent_messages = all_messages[split_index:]

            if len(old_messages) == 0:
                return {
                    "success": True,
                    "message": "No old messages to compact",
                    "messages_before": len(all_messages),
                    "messages_after": len(all_messages)
                }

            logger.info(f"Compacting {len(old_messages)} old messages, keeping {len(recent_messages)} recent messages")

            # 5. Initialize file_read tool for the compaction agent
            file_read_tool = None
            if self.workspace_dir:
                file_read_tool = FileReadTool(workspace_dir=self.workspace_dir)
                logger.info(f"Compaction agent has access to workspace: {self.workspace_dir}")

            # 6. Build compact request: compact system + old messages + user instruction
            compact_messages = [
                {"role": "system", "content": COMPACTION_AGENT_SYSTEM_PROMPT},
                *old_messages,
                {
                    "role": "user",
                    "content": "Summarize the above conversation using the 5-section XML format. Use file_read if needed."
                }
            ]

            # 7. ReAct loop: Let LLM call file_read if needed
            logger.info("Starting compaction agent (with tool access)...")
            max_iterations = 10
            summary_text = None

            for iteration in range(max_iterations):
                logger.info(f"Compaction agent iteration {iteration + 1}/{max_iterations}")

                tools = [file_read_tool.to_openrouter_format()] if file_read_tool else None

                response = await self.llm_provider.chat(
                    messages=compact_messages,
                    tools=tools,
                    temperature=0.2,
                    model="google/gemini-2.5-pro",
                )

                assistant_msg = response.get("choices", [{}])[0].get("message", {})
                content = assistant_msg.get("content")
                tool_calls = assistant_msg.get("tool_calls", [])


                if not tool_calls:
                    compact_messages.append({
                        "role": "assistant",
                        "content": content
                    })
                    summary_text = content
                    logger.info(f"Compaction agent finished after {iteration + 1} iterations")
                    break

                compact_messages.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls
                })

                logger.info(f"Compaction agent calling {len(tool_calls)} tools")
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

                    compact_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result_str
                    })

            if not summary_text:
                logger.error("Compaction agent exceeded max iterations without producing summary")
                return {"success": False, "error": "Compaction agent timeout"}

            logger.info(f"Generated summary: {len(summary_text)} chars")

            # 8. Create summary message with guidance for LLM
            summary_message = {
                "role": "user",
                "content": f"📋 **[Context Summary - Previous Conversation]**\n\n{summary_text}\n\n---\nPlease review the above summary and confirm your understanding of previous work."
            }

            # 9. Let LLM "digest" the summary by generating a confirmation
            logger.info("Calling LLM to confirm understanding of summary...")
            confirmation_messages = system_messages + [summary_message]

            confirmation_response = await self.llm_provider.chat(
                messages=confirmation_messages,
                temperature=0.2,
                model="google/gemini-2.5-pro",
            )

            confirmation_text = confirmation_response.get("choices", [{}])[0].get("message", {}).get("content", "")

            if not confirmation_text:
                confirmation_text = "I understand the previous work and will continue from here."
                logger.warning("LLM returned empty confirmation, using fallback")

            confirmation_message = {
                "role": "assistant",
                "content": confirmation_text
            }

            logger.info(f"LLM confirmation: {confirmation_text[:100]}...")

            # 10. Rebuild: system + [summary, confirmation] + recent_messages + continue prompt
            new_messages = system_messages + [summary_message, confirmation_message] + recent_messages

            # Add "continue" prompt at the end
            continue_message = {
                "role": "user",
                "content": "Good. Please continue your work."
            }
            new_messages.append(continue_message)

            # 11. Replace in MessageManager and persist to disk
            self.message_manager.messages = new_messages
            self.message_manager._save()

            messages_before = len(all_messages)
            messages_after = len(new_messages)
            reduction_pct = ((messages_before - messages_after) / messages_before) * 100

            logger.info(f"Compaction complete: {messages_before} → {messages_after} messages ({reduction_pct:.1f}% reduction)")

            return {
                "success": True,
                "message": f"Context compacted: {messages_before} → {messages_after} messages",
                "messages_before": messages_before,
                "messages_after": messages_after,
                "old_messages_summarized": len(old_messages),
                "recent_messages_kept": len(recent_messages),
                "reduction_percent": round(reduction_pct, 1)
            }

        except Exception as e:
            logger.error(f"Compaction failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
