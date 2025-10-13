"""File Write Tool - Write or append content to files."""

import logging
from pathlib import Path
from typing import Any, Dict

from .base import BaseTool

logger = logging.getLogger(__name__)


class FileWriteTool(BaseTool):
    """Write or append content to files in workspace."""

    def __init__(self, workspace_dir: Path):
        """Initialize with workspace directory.

        Args:
            workspace_dir: Path object for the session workspace directory.
        """
        self.workspace = workspace_dir

    @property
    def name(self) -> str:
        return "file_write"

    @property
    def description(self) -> str:
        return (
            "Write or append content to files in your workspace. "
            "\n\n"
            "📁 Workspace Structure:\n"
            "  • progress.md - Research strategy and plan (overwrite when strategy changes)\n"
            "  • notes.md - Work notes, findings, takeaways (append as you work)\n"
            "  • draft.md - Final answer draft with citations (overwrite when composing)\n"
            "  • cache/ - Cached web content (auto-created by web_search)\n"
            "  • analysis/ - Generated outputs (auto-created by execute_python)\n"
            "\n"
            "🎯 Usage:\n"
            "  • Update strategy: file_write(filename='progress.md', content='...', append=false)\n"
            "  • Add notes: file_write(filename='notes.md', content='...', append=true)\n"
            "  • Write draft: file_write(filename='draft.md', content='...', append=false)\n"
            "  • Save custom file: file_write(filename='cache/my_analysis.txt', content='...')\n"
            "\n"
            "⚙️ Parameters:\n"
            "  • filename: Relative path (e.g., 'notes.md', 'cache/article.txt')\n"
            "  • content: Text to write\n"
            "  • append: true = add to end, false = replace entire file (default: false)"
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "File name or path (e.g., 'notes.md', 'cache/article.txt')"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write"
                },
                "append": {
                    "type": "boolean",
                    "description": "If true, append to existing file; if false, overwrite (default: false)",
                    "default": False
                }
            },
            "required": ["filename", "content"]
        }

    async def execute(self, filename: str, content: str, append: bool = False, **kwargs) -> Dict[str, Any]:
        """Write content to file.

        Args:
            filename: File to write
            content: Content to write
            append: Whether to append (True) or overwrite (False)

        Returns:
            Success status and file info
        """
        try:
            file_path = self._get_file_path(filename)

            if append:
                # Get existing content or empty string
                existing = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
                # Append with newline separator if file already has content
                new_content = existing + ("\n" if existing else "") + content
                file_path.write_text(new_content, encoding="utf-8")

                return {
                    "success": True,
                    "operation": "append",
                    "filename": filename,
                    "appended_size": len(content),
                    "total_size": len(new_content),
                    "message": f"Appended {len(content)} chars to '{filename}'"
                }
            else:
                # Overwrite
                file_path.write_text(content, encoding="utf-8")

                return {
                    "success": True,
                    "operation": "write",
                    "filename": filename,
                    "size": len(content),
                    "message": f"Wrote {len(content)} chars to '{filename}'"
                }

        except Exception as e:
            logger.error(f"File write error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _get_file_path(self, filename: str) -> Path:
        """Get full file path and ensure parent directory exists.

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

        # Create parent directory if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        return file_path
