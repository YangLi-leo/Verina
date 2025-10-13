from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """Base class for all tools.

    Tools wrap existing functionality (SearchEngine, CodeSandbox, etc.)
    to be callable by the Agent via tool calling.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for function calling."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM to understand when to use it."""
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Define tool parameters in OpenRouter format.

        Returns:
            Dict with structure:
            {
                "type": "object",
                "properties": {
                    "param_name": {"type": "string", "description": "..."}
                },
                "required": ["param_name"]
            }
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters.

        Returns:
            Tool execution result (will be stringified for LLM)
        """
        pass

    def to_openrouter_format(self) -> Dict[str, Any]:
        """Convert to OpenRouter function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.get_parameters(),
            },
        }