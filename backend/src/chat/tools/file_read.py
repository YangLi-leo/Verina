"""File Read Tool - Read files from workspace."""

import logging
from pathlib import Path
from typing import Any, Dict

from .base import BaseTool

logger = logging.getLogger(__name__)


class FileReadTool(BaseTool):
    """Read file content from workspace."""

    def __init__(self, workspace_dir: Path):
        """Initialize with workspace directory.

        Args:
            workspace_dir: Path object for the session workspace directory.
        """
        self.workspace = workspace_dir

    @property
    def name(self) -> str:
        return "file_read"

    @property
    def description(self) -> str:
        return (
            "Read content from files in your workspace. "
            "\n\n"
            "📁 Available Files:\n"
            "  • progress.md - Current research strategy and plan\n"
            "  • notes.md - Your work notes and findings\n"
            "  • draft.md - Draft of final answer\n"
            "  • cache/*.md - Cached web articles (auto-saved by web_search)\n"
            "  • analysis/* - Generated outputs (images, data, reports)\n"
            "\n"
            "🎯 Common Uses:\n"
            "  • Review strategy: file_read(filename='progress.md')\n"
            "  • Check notes: file_read(filename='notes.md')\n"
            "  • Read cached article: file_read(filename='cache/article_name.md')\n"
            "  • Review draft: file_read(filename='draft.md')\n"
            "\n"
            "💡 Tip: Use file_list first to see what files exist in your workspace"
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "File name or path (e.g., 'notes.md', 'cache/article.txt')"
                }
            },
            "required": ["filename"]
        }

    async def execute(self, filename: str, **kwargs) -> Dict[str, Any]:
        """Read file content.

        Args:
            filename: File to read

        Returns:
            File content and metadata
        """
        try:
            file_path = self._get_file_path(filename)

            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: '{filename}'",
                    "hint": "Use file_list to see available files"
                }

            content = file_path.read_text(encoding="utf-8")

            return {
                "success": True,
                "filename": filename,
                "content": content,
                "size": len(content)
            }

        except Exception as e:
            logger.error(f"File read error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _get_file_path(self, filename: str) -> Path:
        """Get full file path.

        Args:
            filename: Relative filename or path

        Returns:
            Full file path

        Raises:
            ValueError: If path traversal is detected
        """
        file_path = self.workspace / filename

        # Security: Ensure path is within workspace
        try:
            file_path.resolve().relative_to(self.workspace.resolve())
        except ValueError:
            raise ValueError(f"Invalid filename: path traversal detected")

        return file_path
