"""Tool to signal the agent to stop and provide final answer."""

from typing import Any, Dict
from .base import BaseTool


class StopAnswerTool(BaseTool):
    """Signal to stop ReAct loop and generate final streaming answer."""

    @property
    def name(self) -> str:
        return "stop_answer"

    @property
    def description(self) -> str:
        return (
            "Call this tool when you have gathered enough information and are ready to provide "
            "a comprehensive final answer to the user. This will end the tool-calling loop and "
            "generate a streaming response."
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []  # No parameters needed
        }

    async def execute(self) -> Dict[str, Any]:
        """Execute stop signal and return prompt injection."""
        return {
            "signal": "STOP_AND_ANSWER",
            "prompt": (
                "Based on all the information gathered above, please provide a comprehensive "
                "answer to the user's query. Include relevant citations and references to "
                "the sources you've accessed. Structure your response clearly and be thorough."
            )
        }