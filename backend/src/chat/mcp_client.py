"""Integrate MCP client for agent tool calling."""

import asyncio
import logging
from typing import Dict, List, Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


# MCP Server Configuration (hardcoded)
# Note: MCP servers are pre-installed in Dockerfile for faster startup
MCP_SERVERS = {
    "chrome-devtools": {
        "command": "chrome-devtools-mcp",  # Pre-installed globally via npm
        "args": [
            "--headless",  # Run in headless mode (no UI)
            "--executablePath", "/usr/bin/chromium",  # Use Chromium instead of Chrome
            "--isolated",  # Create isolated temp profile per session (auto-cleanup)
            "--chromeArg=--no-sandbox",  # Required for Docker
            "--chromeArg=--disable-setuid-sandbox",  # Required for Docker
            "--chromeArg=--disable-dev-shm-usage",  # Use /tmp instead of /dev/shm
        ],
        "env": None  # No environment variables needed
    }
    # Add more MCP servers here as needed
    # "another-server": {
    #     "command": "python",
    #     "args": ["path/to/server.py"]
    # }
}


class MCPClient:
    """Integrate MCP client for agent tool calling.

    Manages multiple MCP server connections and provides unified tool access.
    """

    def __init__(self):
        """Initialize MCP client."""
        self.sessions: Dict[str, ClientSession] = {}  # server_name -> session
        self.exit_stack = AsyncExitStack()
        self.tools_cache: Dict[str, List] = {}  # server_name -> tools

    async def connect_all_servers(self) -> Dict[str, List]:
        """Connect to all configured MCP servers.

        Returns:
            Dict mapping server name to list of available tools
        """
        logger.info(f"Connecting to {len(MCP_SERVERS)} MCP servers...")

        for server_name, config in MCP_SERVERS.items():
            try:
                await self._connect_server(server_name, config)
            except Exception as e:
                logger.error(f"Failed to connect to MCP server '{server_name}': {e}", exc_info=True)
                # Continue with other servers even if one fails
                continue

        logger.info(f"Successfully connected to {len(self.sessions)}/{len(MCP_SERVERS)} MCP servers")
        return self.tools_cache

    async def _connect_server(self, server_name: str, config: Dict) -> None:
        """Connect to a single MCP server.

        Args:
            server_name: Name of the server
            config: Server configuration with 'command', 'args', and optional 'env'
        """
        try:
            # Get environment variables from config (if provided)
            env = config.get("env", None)

            server_params = StdioServerParameters(
                command=config["command"],
                args=config["args"],
                env=env
            )

            # Create stdio transport
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            stdio, write = stdio_transport

            # Create session
            session = await self.exit_stack.enter_async_context(
                ClientSession(stdio, write)
            )

            # Initialize session
            await session.initialize()

            # Store session
            self.sessions[server_name] = session

            # List and cache available tools
            response = await session.list_tools()
            tools = response.tools
            self.tools_cache[server_name] = tools

            logger.info(
                f"Connected to MCP server '{server_name}' with {len(tools)} tools: "
                f"{[tool.name for tool in tools]}"
            )

        except Exception as e:
            logger.error(f"Failed to connect to '{server_name}': {e}", exc_info=True)
            raise

    def get_all_tools(self) -> List[Dict]:
        """Get all tools from all connected servers.

        Returns:
            List of tool definitions in format:
            [
                {
                    "server": "chrome-devtools",
                    "name": "take_screenshot",
                    "description": "...",
                    "input_schema": {...}
                },
                ...
            ]
        """
        all_tools = []

        for server_name, tools in self.tools_cache.items():
            for tool in tools:
                all_tools.append({
                    "server": server_name,
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                })

        return all_tools

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict) -> Dict:
        """Call a tool on a specific MCP server.

        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            ValueError: If server not connected or tool not found
        """
        session = self.sessions.get(server_name)
        if not session:
            raise ValueError(f"MCP server '{server_name}' not connected")

        try:
            logger.info(f"Calling MCP tool '{tool_name}' on server '{server_name}' with args: {arguments}")

            result = await session.call_tool(tool_name, arguments)

            logger.info(f"MCP tool '{tool_name}' completed successfully")
            return {
                "success": True,
                "content": result.content,
                "isError": result.isError if hasattr(result, 'isError') else False
            }

        except Exception as e:
            logger.error(f"MCP tool call failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "isError": True
            }

    async def cleanup(self):
        """Clean up all MCP connections."""
        logger.info("Cleaning up MCP connections...")
        try:
            await self.exit_stack.aclose()
            self.sessions.clear()
            self.tools_cache.clear()
            logger.info("MCP cleanup completed")
        except RuntimeError as e:
            # Ignore cancel scope errors during cleanup (harmless in shutdown)
            if "cancel scope" in str(e):
                logger.debug(f"Ignoring cancel scope cleanup error: {e}")
            else:
                logger.error(f"Error during MCP cleanup: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error during MCP cleanup: {e}", exc_info=True)
