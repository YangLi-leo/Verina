"""Agent Mode Agent - Deep research with HIL → Research stages.

This agent handles Agent Mode with two-stage progression:
- HIL (Human-in-the-Loop): Quick search + confirmation
- Research: Full toolset for comprehensive investigation

V3 Updates:
- Refactored to inherit from BaseAgent to reduce code duplication
"""

import json
import logging
import time
import re
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Set

from src.chat.config import ChatConfig
from src.chat.manager import MessageManager
from src.chat.model import ChatResponse, ThinkingStep
from src.chat.tools.base import BaseTool
from src.chat.tools.execute_python import SandboxTool
from src.chat.tools.stop_answer import StopAnswerTool
from src.chat.tools.web_search import WebSearchTool
from src.chat.tools.compact_context import CompactContextTool
from src.chat.tools.start_research import StartResearchTool
from src.chat.tools.file_read import FileReadTool
from src.chat.tools.file_write import FileWriteTool
from src.chat.tools.file_list import FileListTool
from src.chat.tools.research_assistant import ResearchAssistantTool
from src.chat.mcp_client import MCPClient
from src.integrations.llm.openrouter import OpenRouterProvider
from .BaseAgent import BaseAgent

logger = logging.getLogger(__name__)


class AgentModeAgent(BaseAgent):
    """
    Agent Mode with HIL → Research stages.

    Features:
    - Two-stage progression (HIL → Research)
    - Full toolset in Research stage
    - Auto-reset after research completion
    - Uses GPT-5 for deep reasoning
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
        """Initialize Agent Mode Agent.

        Args:
            llm_provider: OpenRouter provider instance
            model: Model to use (defaults to ChatConfig.DEFAULT_MODEL)
            temperature: Sampling temperature
            max_iterations: Maximum ReAct iterations
            session_id: Session identifier for file system workspace
            base_data_dir: Base directory for data storage
            chat_service: ChatService instance for cancellation support
        """
        super().__init__(
            llm_provider=llm_provider,
            model=model or ChatConfig.DEFAULT_MODEL,
            temperature=temperature,
            max_iterations=max_iterations,
            session_id=session_id,
            base_data_dir=base_data_dir,
            workspace_suffix="workspace_agent",
        )

        # Store chat_service reference for cancellation
        self.chat_service = chat_service

        self.mcp_client = MCPClient()

        if self.workspace_dir:
            self._initialize_workspace()

        # Stage management (HIL or Research)
        self.stage = "hil"  # Always start in HIL

        self.tools: Dict[str, BaseTool] = {}
        self.tools_hil: Dict[str, BaseTool] = {}
        self.tools_research: Dict[str, BaseTool] = {}
        self._initialize_tools()

        # Default to HIL tools
        self.tools = self.tools_hil

        logger.info(f"AgentModeAgent initialized in {self.stage} stage with {len(self.tools)} tools")

    def _initialize_workspace(self):
        """Initialize workspace directory structure and files."""
        if not self.workspace_dir:
            return

        logger.info(f"Initializing workspace at {self.workspace_dir}")

        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        (self.workspace_dir / "cache").mkdir(exist_ok=True)
        (self.workspace_dir / "conversations").mkdir(exist_ok=True)
        (self.workspace_dir / "analysis" / "images").mkdir(parents=True, exist_ok=True)
        (self.workspace_dir / "analysis" / "data").mkdir(parents=True, exist_ok=True)
        (self.workspace_dir / "analysis" / "reports").mkdir(parents=True, exist_ok=True)

        progress_file = self.workspace_dir / "progress.md"
        if not progress_file.exists():
            progress_file.write_text(
                "# Research Progress\n\n"
                "## Strategy\n"
                "Document your research strategy and plan here.\n\n"
                "## Status\n"
                "Track your current progress.\n",
                encoding="utf-8"
            )

        notes_file = self.workspace_dir / "notes.md"
        if not notes_file.exists():
            notes_file.write_text(
                "# Work Notes\n\n"
                "Record your analysis, takeaways, and findings here during the research process.\n\n",
                encoding="utf-8"
            )

        draft_file = self.workspace_dir / "draft.md"
        if not draft_file.exists():
            draft_file.write_text(
                "# Draft Answer\n\n"
                "Compose your final answer here. Use [1][2] for citations.\n\n",
                encoding="utf-8"
            )

        logger.info(f"Workspace initialized with {len(list(self.workspace_dir.rglob('*')))} items")

    def _initialize_tools(self):
        """Initialize HIL and Research toolsets."""
        from src.core.config import Config

        # Shared tools
        web_search_tool = WebSearchTool(workspace_dir=self.workspace_dir)
        stop_answer_tool = StopAnswerTool()
        start_research_tool = StartResearchTool()

        # HIL stage tools: quick search + confirmation
        self.tools_hil = {
            web_search_tool.name: web_search_tool,
            start_research_tool.name: start_research_tool,
        }

        # Research stage: full toolset
        compact_context_tool = CompactContextTool(
            llm_provider=self.llm_provider,
            workspace_dir=self.workspace_dir
        )

        self.tools_research = {
            web_search_tool.name: web_search_tool,
            stop_answer_tool.name: stop_answer_tool,
            compact_context_tool.name: compact_context_tool,
        }

        # Add SandboxTool only if E2B_API_KEY is configured
        if Config.has_e2b_key():
            sandbox_tool = SandboxTool(workspace_dir=self.workspace_dir)
            self.tools_research[sandbox_tool.name] = sandbox_tool
            logger.info("✓ SandboxTool (execute_python) enabled - E2B_API_KEY configured")
        else:
            logger.info("⚠ SandboxTool (execute_python) disabled - E2B_API_KEY not configured")

        if self.workspace_dir:
            file_read_tool = FileReadTool(workspace_dir=self.workspace_dir)
            file_write_tool = FileWriteTool(workspace_dir=self.workspace_dir)
            file_list_tool = FileListTool(workspace_dir=self.workspace_dir)
            research_assistant_tool = ResearchAssistantTool(
                llm_provider=self.llm_provider,
                workspace_dir=self.workspace_dir
            )

            self.tools_research[file_read_tool.name] = file_read_tool
            self.tools_research[file_write_tool.name] = file_write_tool
            self.tools_research[file_list_tool.name] = file_list_tool
            self.tools_research[research_assistant_tool.name] = research_assistant_tool

        logger.info(f"Initialized Agent HIL tools: {list(self.tools_hil.keys())}")
        logger.info(f"Initialized Agent Research tools: {list(self.tools_research.keys())}")

    def reset_to_hil(self):
        """Reset agent to HIL stage after research completion."""
        logger.info("[Agent] Resetting to HIL stage")
        self.stage = "hil"
        self.tools = self.tools_hil

    def _get_tools_for_openrouter(self) -> List[Dict[str, Any]]:
        """Get tools in OpenRouter format."""
        return [tool.to_openrouter_format() for tool in self.tools.values()]

    def _process_web_search_for_agent(self, result: Dict) -> tuple[str, List[Dict]]:
        """Process web_search for Agent Mode - no [1][2] numbers in LLM output.

        formatted_text → LLM (no citation numbers, just bullet points)
        sources → frontend (with idx for citation rendering)
        """
        if result.get("error") or not result.get("results"):
            error_text = result.get("error", "No results found")
            return (f"Search failed: {error_text}", [])

        # Collect sources for frontend
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

            # Format for LLM (no [1][2], just bullet points)
            formatted_lines.append(f"• {r['title']}")
            formatted_lines.append(f"  URL: {r['url']}")
            if r.get("cache_path"):
                formatted_lines.append(f"  Cached: {r['cache_path']}")
            if r.get("age"):
                formatted_lines.append(f"  Published: {r['age']}")
            if r.get("snippet"):
                formatted_lines.append(f"  {r['snippet']}")
            formatted_lines.append("")

        formatted_text = "\n".join(formatted_lines)

        self.current_sources = sources

        return (formatted_text, sources)

    async def _execute_tool(self, tool_call: Dict[str, Any], tools: Dict) -> tuple[str, Optional[List[Dict]]]:
        """Execute a single tool call - override for Agent Mode web_search handling.

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
                # Use Agent-specific processing (no [1][2] in LLM output)
                return self._process_web_search_for_agent(result)
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

    async def _switch_to_research_stage(self, message_manager: MessageManager):
        """Switch from HIL stage to research stage."""
        logger.info("[Stage Switch] Switching from HIL to research stage")

        self.stage = "research"

        # Switch toolset
        self.tools = self.tools_research

        if self.workspace_dir and not self.workspace_dir.exists():
            self._initialize_workspace()

        # Inject message_manager dependency for compact_context
        compact_tool = self.tools.get("compact_context")
        if compact_tool:
            compact_tool.message_manager = message_manager

        try:
            logger.info("[Stage Switch] Loading MCP tools...")
            await self.mcp_client.connect_all_servers()

            from src.chat.tools.mcp_tool import MCPTool

            mcp_tool_definitions = self.mcp_client.get_all_tools()

            for tool_def in mcp_tool_definitions:
                mcp_tool = MCPTool(
                    mcp_client=self.mcp_client,
                    server_name=tool_def["server"],
                    tool_name=tool_def["name"],
                    description=tool_def["description"],
                    input_schema=tool_def["input_schema"]
                )

                self.tools[mcp_tool.name] = mcp_tool

            logger.info(
                f"[Stage Switch] Loaded {len(mcp_tool_definitions)} MCP tools from "
                f"{len(self.mcp_client.sessions)} servers"
            )

        except Exception as e:
            logger.error(f"[Stage Switch] Failed to load MCP tools: {e}", exc_info=True)
            # Continue without MCP tools

        logger.info(f"[Stage Switch] Research stage activated with {len(self.tools)} tools")

    async def agent_stream(
        self,
        message: str,
        user_id: str,
        session_id: str,
        message_manager: MessageManager,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream agent mode with HIL → Research stages.

        Args:
            message: User's message
            user_id: User identifier
            session_id: Session identifier
            message_manager: Message manager for conversation history

        Yields:
            - {"type": "stage_switch", "data": {"stage": str}} - stage transition
            - {"type": "thinking_step", "data": ThinkingStep} - tool execution (Research stage only)
            - {"type": "complete", "data": ChatResponse} - at the end
        """
        start_time = time.time()
        thinking_steps: List[ThinkingStep] = []
        tools_used_set: Set[str] = set()
        step_counter = 0

        # Reset current sources for new response
        self.current_sources = []

        message_manager.add_user_message(message)

        if self.workspace_dir and not self.workspace_dir.exists():
            try:
                self.workspace_dir.mkdir(parents=True, exist_ok=True)

                progress_template = """# Progress

<!-- Flexible strategic plan - overwrite when strategy changes
- Overall goal: [What does user want?]
- Current stage: [Research? Analysis? Writing?]
- Strategy: [Current plan]
-->
"""
                (self.workspace_dir / "progress.md").write_text(progress_template, encoding="utf-8")

                references_template = """# References

<!-- Analysis notes for each article
- Key information and data
- Ideas and insights
- Valuable quotes
-->
"""
                (self.workspace_dir / "notes.md").write_text(references_template, encoding="utf-8")

                draft_template = """# Draft

<!-- Compose final answer based on notes.md
- Organize ideas and refine wording
- Use [1][2] for citations
- Add References section at end
-->
"""
                (self.workspace_dir / "draft.md").write_text(draft_template, encoding="utf-8")

                (self.workspace_dir / "cache").mkdir(exist_ok=True)

                logger.info(f"Workspace initialized with 4 template files: {self.workspace_dir}")
            except Exception as e:
                logger.warning(f"Failed to create workspace directory: {e}")

        # ReAct Loop
        iteration = 0
        ready_for_final_answer = False
        last_prompt_tokens = 0

        try:
            while iteration < self.max_iterations:
                iteration += 1
                logger.info(f"[Agent] Iteration {iteration}/{self.max_iterations} (stage: {self.stage})")

                # Check for cancellation
                if self.chat_service and self.chat_service.cancel_flags.get(session_id):
                    logger.info(f"[Agent] Cancelled by user at iteration {iteration} (stage: {self.stage})")

                    # Reset to HIL if in research stage
                    if self.stage == "research":
                        logger.info("[Agent Cancellation] Resetting from research to HIL")
                        self.reset_to_hil()

                    # Clean workspace
                    if self.workspace_dir and self.workspace_dir.exists():
                        logger.info("[Agent Cancellation] Cleaning workspace")
                        self._clean_workspace_after_research()

                    # Clear the cancel flag
                    self.chat_service.clear_cancel_flag(session_id)

                    final_response = "Research stopped by user."

                    # Yield cancellation event
                    yield {
                        "type": "cancelled",
                        "message": "Stopped by user",
                        "steps_completed": len(thinking_steps),
                        "stage": self.stage
                    }

                    break  # Exit loop

                try:
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

                        # Cache info
                        prompt_details = usage.get("prompt_tokens_details", {})
                        cached_tokens = prompt_details.get("cached_tokens", 0)

                        logger.info(
                            f"📊 Context: {last_prompt_tokens} tokens (cached: {cached_tokens}) | Total: {total_tokens}"
                        )

                    message_data = response["choices"][0]["message"]

                    # Extract outputs
                    reasoning = message_data.get("reasoning", "")
                    content = message_data.get("content", "")
                    tool_calls = message_data.get("tool_calls")

                    if reasoning:
                        logger.info(f"[Agent] GPT-5 reasoning: {reasoning[:100]}...")

                    # Check if LLM wants to use tools
                    if tool_calls:
                        # Check for start_research (stage switch)
                        has_start_research = any(
                            tc["function"]["name"] == "start_research"
                            for tc in tool_calls
                        )

                        if has_start_research:
                            # Switch to research mode
                            logger.info("[Agent] start_research called, switching to research mode")

                            # Execute the tool to get guidance
                            start_tool = self.tools.get("start_research")
                            result = await start_tool.execute()

                            # Switch stage
                            await self._switch_to_research_stage(message_manager)

                            # Notify frontend
                            yield {"type": "stage_switch", "data": {"stage": "research"}}

                            # Inject guidance to LLM
                            message_manager.add_user_message(result["guidance"])

                            # Continue loop (LLM will now see full toolset)
                            continue

                        # Check for stop_answer
                        has_stop_answer = any(
                            tc["function"]["name"] == "stop_answer"
                            for tc in tool_calls
                        )

                        if has_stop_answer:
                            # stop_answer called - prepare for final output
                            logger.info("[Agent] stop_answer called")
                            stop_tool = self.tools.get("stop_answer")
                            result = await stop_tool.execute()

                            # For research stage: inject blog generation prompt
                            # For HIL stage: inject regular final answer prompt
                            if self.stage == "research":
                                # Load research materials from workspace files
                                draft_content = ""
                                notes_content = ""

                                if self.workspace_dir and self.workspace_dir.exists():
                                    try:
                                        draft_file = self.workspace_dir / "draft.md"
                                        if draft_file.exists():
                                            draft_content = draft_file.read_text(encoding="utf-8")
                                            logger.info(f"[Blog Generation] Loaded draft.md ({len(draft_content)} chars)")

                                        notes_file = self.workspace_dir / "notes.md"
                                        if notes_file.exists():
                                            notes_content = notes_file.read_text(encoding="utf-8")
                                            logger.info(f"[Blog Generation] Loaded notes.md ({len(notes_content)} chars)")
                                    except Exception as e:
                                        logger.error(f"[Blog Generation] Failed to load research files: {e}")

                                # Construct blog prompt with injected content
                                blog_prompt = f"""Research completed! Your research materials are provided below.

## Your Research Materials

### draft.md (Your organized research with citations):
---
{draft_content}
---

### notes.md (Additional insights and observations):
---
{notes_content}
---

## Now Generate the HTML Blog

You have been provided with your complete research materials (draft.md and notes.md) above. Use them as your primary source.

Take a deep breath and think step by step.

## Step 1: Understand What You Have

- Your draft.md contains the organized findings with proper citations [1][2][3]...
- Your notes.md has additional insights, quotes, and observations
- These files represent hours of research, searches, and reading
- **Use them as the foundation** - don't rely solely on memory

## Step 2: Generate Two Deliverables

### Deliverable 1: Brief Overview (2-3 paragraphs)
Write a concise summary that:
- Highlights the key findings from your research
- References the thinking process that led you there
- Tells the user there's a full interactive report below

### Deliverable 2: Deep Technical Blog (HTML Format)

Now, carefully craft a comprehensive technical blog in HTML format. **Focus on depth and clarity, not fancy interactions.**

Think of this as a high-quality Medium or Substack article - the kind you'd read to deeply understand a topic.

#### Content Structure (Prioritize depth over interactivity):
1. **Title & Executive Summary**: Hook the reader, preview key insights
2. **Introduction**: Context, why this matters, research question
3. **Background/Context**: Essential knowledge readers need
4. **Methodology** (if relevant): How you investigated this (reference your thinking steps)
5. **Core Analysis**: This is the meat - break down complex ideas into digestible sections
   - Use clear headings and subheadings
   - Include code examples, diagrams (ASCII art if needed), or tables
   - Explain WHY, not just WHAT
6. **Deep Dives**: Detailed exploration of interesting aspects
7. **Practical Implications**: So what? Why should readers care?
8. **Related Topics**: Connections to broader themes
9. **Conclusion**: Key takeaways and future directions
10. **References**: Clickable citations with [title, URL, date]

#### Design Specifications (Notion-inspired minimalism):

**Typography:**
- Font family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif
- Headings: 24px (h1), 20px (h2), 16px (h3)
- Body text: 16px, line-height 1.6
- Color: #37352f (primary text), #787774 (secondary)

**Layout:**
- Max content width: 800px
- Generous padding: 40px sides on desktop, 20px on mobile
- White background (#ffffff)
- Subtle borders: 1px solid #e5e5e5

**Content Elements (focus on readability):**
1. **Headings hierarchy**: Clear h1 → h2 → h3 structure
2. **Code blocks** (if needed):
   - Monospace font (Consolas, Monaco, 'Courier New')
   - Light gray background (#f6f8fa)
   - Syntax highlighting with inline styles (optional, not required)
3. **Blockquotes** for important quotes or insights
   - Left border accent (#e5e5e5)
   - Italic or distinct styling
4. **Tables** for comparisons or data
   - Clean borders, alternating row colors
5. **Lists** (bullet/numbered) for clarity
   - Proper indentation and spacing
6. **Inline code**: Distinct styling for technical terms
7. **Images/Diagrams** (if generated):
   - Base64 embedded or ASCII art
   - Clear captions below

**Optional enhancements** (nice to have, not required):
- Simple table of contents (basic <ul> list linking to sections)
- Smooth scroll CSS for anchor links
- Collapsible sections using <details>/<summary> (only if content is very long)

#### Technical Requirements:

- **All CSS must be inline** in a <style> tag
- **All JavaScript must be inline** in a <script> tag
- **No external dependencies** - no CDN links, no external images
- **Responsive design** - mobile-first approach with media queries
- **Semantic HTML5** - proper heading hierarchy, sections, articles
- **Accessibility** - ARIA labels, proper contrast ratios
- **Print-friendly** - @media print styles

#### References Format (CRITICAL):

**All citations must be clickable links!**

```html
<h2>References</h2>
<ol>
  <li>
    <a href="https://example.com/article" target="_blank" rel="noopener noreferrer">
      Article Title Here
    </a>
    - Brief description or key point
  </li>
</ol>
```

Style references with:
- Distinct link color (#0066cc or #2e7d32)
- Underline on hover
- External link indicator (optional)

#### Quality Checklist (Review before finalizing):

- [ ] HTML is valid and well-formatted
- [ ] Content is DEEP - explains complex concepts clearly
- [ ] Analysis shows original thinking, not just summarization
- [ ] **All references are clickable <a> tags with proper URLs**
- [ ] Code examples (if any) are practical and well-explained
- [ ] Headings create a logical flow
- [ ] Mobile-friendly layout (readable on small screens)
- [ ] No broken links or missing content

## Final Output Format:

First, output your brief overview text (2-3 paragraphs).

Then, output the complete HTML in a code block like this:

```html
<!DOCTYPE html>
<html lang="en">
...your complete HTML here...
</html>
```

**Remember:** Take your time. Think through each section carefully. Reference your thinking steps. Create something you'd be proud to share."""
                                message_manager.add_user_message(blog_prompt)
                            else:
                                # HIL stage: use regular prompt
                                message_manager.add_user_message(result["prompt"])

                            ready_for_final_answer = True
                            break

                        # Normal tools - execute them
                        message_manager.add_assistant_message(
                            content=reasoning if reasoning else None,
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

                            thinking_step = self._create_thinking_step(
                                step=step_counter,
                                tool_name=tool_name,
                                tool_args=tool_args,
                                tool_result=tool_result,
                                reasoning=reasoning if reasoning else None,  # GPT-5 reasoning
                            )
                            thinking_steps.append(thinking_step)

                            # Yield thinking step to frontend (real-time streaming for both HIL and research)
                            yield {"type": "thinking_step", "data": thinking_step.model_dump(mode='json')}

                            message_manager.add_tool_result(
                                tool_call_id=tool_call["id"], content=tool_result
                            )

                        # Add context usage info after tool results
                        if last_prompt_tokens > 0:
                            context_usage_percent = (last_prompt_tokens / ChatConfig.CONTEXT_LIMIT) * 100
                            context_info = f'<context_usage tokens="{last_prompt_tokens}" limit="{ChatConfig.CONTEXT_LIMIT}" usage="{context_usage_percent:.1f}%" />'
                            message_manager.add_user_message(context_info)

                        # Check context size and trigger compaction if needed
                        if last_prompt_tokens > ChatConfig.AUTO_COMPACT_THRESHOLD:
                            logger.warning(f"Context size {last_prompt_tokens} exceeds {ChatConfig.AUTO_COMPACT_THRESHOLD} tokens, forcing compaction")
                            compact_tool = self.tools.get("compact_context")
                            if compact_tool:
                                compact_result = await compact_tool.execute(keep_recent_user_messages=10)
                                logger.info(f"Forced context compaction completed: {compact_result}")

                        # Continue loop
                        continue

                    else:
                        # No tool calls
                        if self.stage == "hil":
                            # HIL stage: LLM provides direct response (initial conclusion + clarification)
                            logger.info("[Agent] HIL stage: LLM providing direct response")

                            final_response = content if content else reasoning

                            if final_response:
                                message_manager.add_assistant_message(content=final_response)
                            else:
                                final_response = "I need more information to provide an answer."
                                message_manager.add_assistant_message(content=final_response)

                            # Add to chat history and get response_id
                            response_id = self._add_response_to_history(
                                user_message=message,
                                assistant_message=final_response,
                                sources=self.current_sources,
                                thinking_steps=thinking_steps if thinking_steps else None,
                                total_time_ms=int((time.time() - start_time) * 1000),
                                mode="agent",
                                prompt_tokens=last_prompt_tokens if last_prompt_tokens > 0 else None,
                                stage="hil",
                            )

                            # Build response and end
                            chat_response = ChatResponse(
                                response_id=response_id,
                                session_id=session_id,
                                user_id=user_id,
                                user_message=message,
                                assistant_message=final_response,
                                thinking_steps=thinking_steps if thinking_steps else None,
                                sources=self.current_sources if self.current_sources else None,
                                used_tools=len(thinking_steps) > 0,
                                has_code=False,
                                has_web_results=any(step.tool == "web_search" for step in thinking_steps),
                                total_time_ms=int((time.time() - start_time) * 1000),
                                model_used=self.model,
                                temperature=self.temperature,
                                prompt_tokens=last_prompt_tokens if last_prompt_tokens > 0 else None,
                            )

                            # Clean workspace after HIL completion (if exists)
                            if self.workspace_dir and self.workspace_dir.exists():
                                self._clean_workspace_after_research()

                            yield {"type": "complete", "data": chat_response.model_dump(mode='json')}
                            return

                        else:
                            # Research stage: must call tools or stop_answer
                            logger.warning("[Agent] Research stage: LLM must call tools or stop_answer")

                            if reasoning or content:
                                message_manager.add_assistant_message(
                                    content=reasoning if reasoning else content
                                )

                            # Inject error correction prompt
                            error_prompt = (
                                "ERROR: In research stage, you must call tools.\n\n"
                                "RULES:\n"
                                "1. Need more info → call web_search, execute_python, file_write, etc.\n"
                                "2. Ready to answer → call stop_answer\n\n"
                                "What tool do you want to use?"
                            )
                            message_manager.add_user_message(error_prompt)
                            continue

                except Exception as e:
                    logger.error(f"Error in ReAct loop: {e}", exc_info=True)
                    error_msg = f"Error during processing: {str(e)}"
                    message_manager.add_assistant_message(content=error_msg)

                    # Clean workspace on error
                    if self.workspace_dir and self.workspace_dir.exists():
                        logger.info("[Agent Error] Cleaning workspace after error")
                        self._clean_workspace_after_research()

                    yield {"type": "error", "data": error_msg}
                    return

            # Generate final answer if ready
            if ready_for_final_answer:
                logger.info("[Agent] Generating final answer")

                # Call LLM (no streaming - get complete response)
                response = await self.llm_provider.chat(
                    messages=message_manager.get_messages(),
                    model=self.model,
                    temperature=self.temperature,
                )

                final_response = response["choices"][0]["message"]["content"]

                usage = response.get("usage", {})
                if usage:
                    last_prompt_tokens = usage.get("prompt_tokens", 0)
                    logger.info(f"Final answer context size: {last_prompt_tokens} tokens")

                # Add complete response to message history
                message_manager.add_assistant_message(content=final_response)

                # AUTO-RESET: If in research stage, reset to HIL after completion
                if self.stage == "research":
                    logger.info("[Agent] Auto-reset to HIL after research completion")
                    self.reset_to_hil()
            else:
                # Hit max iterations without stop_answer
                logger.warning("Hit max iterations without final answer")
                final_response = "I need more iterations to complete this request."
                message_manager.add_assistant_message(content=final_response)

        finally:
            # Cleanup sandbox only
            self._cleanup_sandbox_only(self.tools)

        total_time_ms = int((time.time() - start_time) * 1000)

        # Extract HTML Artifact (if Research stage completed)
        artifact = None
        assistant_message = final_response

        if ready_for_final_answer and "<!DOCTYPE html>" in final_response:
            # Try to extract HTML from response
            html_pattern = r'```html\s*(<!DOCTYPE html>.*?</html>)\s*```'
            html_match = re.search(html_pattern, final_response, re.DOTALL | re.IGNORECASE)

            if not html_match:
                # Pattern 2: Direct HTML without code block
                html_pattern = r'<!DOCTYPE html>.*?</html>'
                html_match = re.search(html_pattern, final_response, re.DOTALL | re.IGNORECASE)

            if html_match:
                # Extract HTML
                html_code = html_match.group(1) if html_match.lastindex else html_match.group(0)
                html_code = html_code.strip()

                # Extract overview (everything before HTML)
                overview_text = final_response[:html_match.start()].strip()
                # Clean up markdown artifacts
                overview_text = overview_text.replace('```html', '').replace('```', '').strip()

                # Extract title from HTML
                title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_code, re.IGNORECASE)
                blog_title = title_match.group(1) if title_match else "Research Report"
                # Remove HTML tags from title
                blog_title = re.sub(r'<[^>]+>', '', blog_title).strip()

                if self.workspace_dir:
                    artifact_path = self.workspace_dir / "artifact.html"
                    artifact_path.write_text(html_code, encoding='utf-8')

                    logger.info(f"[Artifact] Generated blog: {blog_title} ({len(html_code)//1024}KB)")

                    artifact = {
                        "type": "html_blog",
                        "title": blog_title,
                        "html_content": html_code,
                        "file_path": str(artifact_path),
                        "file_size_kb": len(html_code) // 1024
                    }

                    # Update assistant_message to only contain overview
                    assistant_message = overview_text if overview_text else "Research completed. See interactive report below."

                    logger.info(f"[Artifact] Overview: {len(assistant_message)} chars")
            else:
                # No HTML artifact found - this is normal for most research queries
                logger.debug("[Artifact] No HTML artifact in response (expected for most queries)")

        # Determine characteristics
        has_code = any(step.has_code for step in thinking_steps)
        has_web_results = any(step.tool == "web_search" for step in thinking_steps)

        # Add to chat history and get response_id
        response_id = self._add_response_to_history(
            user_message=message,
            assistant_message=assistant_message,
            sources=self.current_sources,
            thinking_steps=thinking_steps if thinking_steps else None,
            total_time_ms=total_time_ms,
            mode="agent",
            prompt_tokens=last_prompt_tokens if last_prompt_tokens > 0 else None,
            artifact=artifact,
            stage=self.stage,
        )

        chat_response = ChatResponse(
            response_id=response_id,
            session_id=session_id,
            user_id=user_id,
            user_message=message,
            assistant_message=assistant_message,  # Overview only (if artifact extracted)
            thinking_steps=thinking_steps if thinking_steps else None,
            sources=self.current_sources if self.current_sources else None,  # Add sources for frontend
            mode="agent",  # Indicate this is from agent mode
            used_tools=len(thinking_steps) > 0,
            has_code=has_code,
            has_web_results=has_web_results,
            total_time_ms=total_time_ms,
            model_used=self.model,
            temperature=self.temperature,
            prompt_tokens=last_prompt_tokens if last_prompt_tokens > 0 else None,
            artifact=artifact,  # HTML blog artifact (if generated)
        )

        # Clean workspace after research completion
        if self.workspace_dir and self.workspace_dir.exists():
            self._clean_workspace_after_research()

        # Yield complete signal
        yield {"type": "complete", "data": chat_response.model_dump(mode='json')}

    def _clean_workspace_after_research(self):
        """Clean workspace directory after research completion.

        This removes all temporary files from the research session:
        - cache/ (downloaded articles)
        - conversations/ (research_assistant dialogues)
        - analysis/ (Python execution outputs)
        - notes.md, draft.md, progress.md (research workspace files)
        - artifact.html (final report - already saved in chat_history)

        The workspace will be recreated fresh for the next research session.
        """
        import shutil

        try:
            if self.workspace_dir and self.workspace_dir.exists():
                logger.info(f"[Cleanup] Removing workspace after research completion: {self.workspace_dir}")
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