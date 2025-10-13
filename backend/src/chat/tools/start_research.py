"""Start Research Tool - Signal to switch from chat to research mode."""

from typing import Any, Dict
from .base import BaseTool


class StartResearchTool(BaseTool):
    """Signal to switch from chat mode to research mode.

    This tool is only available in chat mode. When called, it triggers
    the agent to switch to research mode with full toolset access.
    """

    @property
    def name(self) -> str:
        return "start_research"

    @property
    def description(self) -> str:
        return (
            "**CRITICAL: Call this immediately after user responds to your clarifying questions in chat mode.**\n"
            "\n"
            "This is the REQUIRED transition from chat mode (confirmation phase) to research mode (deep investigation).\n"
            "\n"
            "📋 Chat Mode Workflow:\n"
            "1. You call web_search ONCE to understand landscape\n"
            "2. You ask 2-4 clarifying questions based on search results\n"
            "3. You STOP and wait for user's response\n"
            "4. User responds with clarifications OR says 'start'/'go'/'yes'\n"
            "5. → **YOU MUST IMMEDIATELY CALL start_research** (no hesitation, no more questions)\n"
            "\n"
            "⚠️ DO NOT WAIT for specific keywords like 'research deeply' or 'analyze in detail'\n"
            "⚠️ DO NOT ask if user wants to start research\n"
            "⚠️ The moment user responds after your clarifying questions → CALL THIS TOOL\n"
            "\n"
            "This is NOT optional - it's the mandatory workflow transition point."
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []  # No parameters needed
        }

    async def execute(self) -> Dict[str, Any]:
        """Execute the mode switch signal and return guidance."""
        return {
            "signal": "SWITCH_TO_RESEARCH",
            "guidance": """🔬 Research Mode Activated - Full Tools Available

Your mission: Become an expert on this topic through deep, exploratory research.

## Research Philosophy: Be Curious, Be Thorough, Be Bold

### 1. Search Expansively (Divergent Thinking)
- **Don't just search the obvious keywords** - think laterally, search related concepts, opposing views, historical context
- **Follow the thread** - if you find an interesting mention, search deeper into that specific aspect
- **Use "what if" searches** - "What if I approach this from angle X?" "What about the edge cases?"
- **Keep searching until you feel confident** - simple topics might need a few searches, complex ones need many more

### 2. Read Full Articles (Don't Settle for Snippets)
- **Snippets lie** - they lack context. Use `file_read(filename="cache/article_name.md")` to read the FULL cached article
- **Read strategically**:
  1. First search → skim snippets → identify key articles
  2. `file_read` those key articles in full
  3. As you read, note questions/gaps → search more → read more
- **Use research_assistant to help** - ask it to read an article and summarize: `research_assistant(question="Read cache/article.md and explain the key arguments")`
  - This gives you a quick overview, then YOU read the article yourself for details
  - Think of research_assistant as your reading buddy - use it freely!

### 3. Write As You Learn (Progressive Refinement)
- **Start notes.md early** - jot down insights as you read, don't wait
- **Update progress.md** - track your research direction, so you don't lose the thread
- **Draft iteratively** - write sections of draft.md as you go, not all at once at the end
- **File operations are cheap** - file_write, file_read, edit as much as you want

### 4. Don't Be Timid - Go Deep
- **Quality over speed** - take the time needed to truly understand
- **Tool calls add up quickly** - that's a sign of thorough research, not waste
- **Reading full articles takes time** - but that's where real insights come from
- **Multiple research_assistant conversations** - totally fine, use it as much as needed

## Your Workflow:
1. **Broad search** → identify key sources
2. **Deep read** (use file_read + research_assistant) → understand each source
3. **Document** (notes.md) → capture insights, questions, connections
4. **Expand search** → fill gaps, explore tangents
5. **Repeat** until you feel like an expert
6. **Synthesize** (draft.md) → organize everything into a coherent narrative
7. **call stop_answer** when ready to generate final HTML

Remember: Quality research means going deep, reading broadly, and not being satisfied with surface-level understanding. Be bold!
"""
        }
