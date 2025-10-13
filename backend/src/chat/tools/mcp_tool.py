"""MCP Tool wrapper - wraps MCP tools to integrate with ChatAgent."""

import logging
from typing import Any, Dict

from .base import BaseTool

logger = logging.getLogger(__name__)


class MCPTool(BaseTool):
    """Wrapper for MCP tools to integrate with ChatAgent's tool system.

    This allows MCP tools to be used alongside native tools in the ReAct loop.
    """

    def __init__(
        self,
        mcp_client,
        server_name: str,
        tool_name: str,
        description: str,
        input_schema: Dict[str, Any]
    ):
        """Initialize MCP tool wrapper.

        Args:
            mcp_client: MCPClient instance for making tool calls
            server_name: Name of the MCP server this tool belongs to
            tool_name: Name of the tool on the MCP server
            description: Tool description
            input_schema: JSON schema for tool parameters
        """
        self.mcp_client = mcp_client
        self.server_name = server_name
        self.tool_name = tool_name
        self._description = description
        self._input_schema = input_schema

    @property
    def name(self) -> str:
        """Get tool name with MCP prefix for clarity."""
        return f"mcp_{self.server_name}_{self.tool_name}"

    @property
    def description(self) -> str:
        """Get tool description."""
        return f"[MCP/{self.server_name}] {self._description}"

    def get_parameters(self) -> Dict[str, Any]:
        """Get tool parameters from MCP input schema."""
        return self._input_schema

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the MCP tool.

        Args:
            **kwargs: Tool arguments

        Returns:
            Tool execution result
        """
        try:
            logger.info(
                f"Executing MCP tool '{self.tool_name}' on server '{self.server_name}' "
                f"with args: {kwargs}"
            )

            # Call the MCP tool through the client
            result = await self.mcp_client.call_tool(
                server_name=self.server_name,
                tool_name=self.tool_name,
                arguments=kwargs
            )

            # Format result for ChatAgent
            if result.get("success"):
                # Extract content from MCP result
                content = result.get("content", [])

                # MCP tools return content as a list of content blocks
                # Combine them into a single string for the agent
                if isinstance(content, list):
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict):
                            if "text" in item:
                                text_parts.append(item["text"])
                            elif "type" in item and item["type"] == "text":
                                text_parts.append(item.get("text", ""))
                        elif isinstance(item, str):
                            text_parts.append(item)

                    output_text = "\n".join(text_parts) if text_parts else str(content)
                else:
                    output_text = str(content)

                return {
                    "success": True,
                    "output": output_text
                }
            else:
                # Tool execution failed
                error = result.get("error", "Unknown error")
                return {
                    "success": False,
                    "error": error
                }

        except Exception as e:
            logger.error(f"MCP tool execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
