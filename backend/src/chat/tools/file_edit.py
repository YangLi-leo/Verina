"""File Edit Tool - Edit files in workspace by replacing text."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .base import BaseTool

logger = logging.getLogger(__name__)


class FileEditTool(BaseTool):
    """Edit files in workspace by replacing old text with new text."""

    def __init__(self, workspace_dir: Optional[Path] = None):
        """Initialize file edit tool.

        Args:
            workspace_dir: Workspace directory containing files to edit
        """
        self.workspace_dir = workspace_dir

    @property
    def name(self) -> str:
        return "file_edit"

    @property
    def description(self) -> str:
        return (
            "Edit files in workspace by replacing text. "
            "Provide the exact old text to find and the new text to replace it with. "
            "Returns success with what was replaced, or error if text not found. "
            "Use this to modify content in draft.md, notes.md, or other workspace files."
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": (
                        "Path to file in workspace (e.g., 'draft.md', 'notes.md'). "
                        "Can be relative to workspace or absolute path."
                    )
                },
                "old_text": {
                    "type": "string",
                    "description": (
                        "Exact text to find and replace. Must match exactly (including whitespace). "
                        "Should be unique enough to avoid ambiguity."
                    )
                },
                "new_text": {
                    "type": "string",
                    "description": "New text to replace the old text with."
                }
            },
            "required": ["file_path", "old_text", "new_text"]
        }

    async def execute(
        self,
        file_path: str,
        old_text: str,
        new_text: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Edit a file by replacing old text with new text.

        Args:
            file_path: Path to file (relative to workspace or absolute)
            old_text: Exact text to find and replace
            new_text: New text to replace with

        Returns:
            Dict with success status and message, or error details
        """
        if not self.workspace_dir:
            return {
                "success": False,
                "error": "No workspace configured."
            }

        try:
            # Resolve file path
            if Path(file_path).is_absolute():
                full_path = Path(file_path)
            else:
                full_path = self.workspace_dir / file_path

            # Security check - ensure file is within workspace
            if not str(full_path.resolve()).startswith(str(self.workspace_dir.resolve())):
                return {
                    "success": False,
                    "error": f"Security error: File path outside workspace: {file_path}"
                }

            # Check if file exists
            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}"
                }

            original_content = full_path.read_text(encoding="utf-8")

            # Check if old_text exists in file
            if old_text not in original_content:
                return {
                    "success": False,
                    "error": (
                        f"Text not found in {file_path}. "
                        f"The old_text must match exactly including whitespace and newlines. "
                        f"File contains {len(original_content)} characters."
                    )
                }

            # Check if old_text appears multiple times
            occurrences = original_content.count(old_text)
            if occurrences > 1:
                return {
                    "success": False,
                    "error": (
                        f"Ambiguous replacement: Text appears {occurrences} times in {file_path}. "
                        f"Please provide more surrounding context in old_text to make it unique."
                    )
                }

            # Perform replacement
            new_content = original_content.replace(old_text, new_text)

            # Write back to file
            full_path.write_text(new_content, encoding="utf-8")

            logger.info(f"File edited: {file_path}, replaced {len(old_text)} chars with {len(new_text)} chars")

            return {
                "success": True,
                "message": f"Successfully edited {file_path}",
                "replaced": {
                    "old_text": old_text[:100] + ("..." if len(old_text) > 100 else ""),
                    "new_text": new_text[:100] + ("..." if len(new_text) > 100 else ""),
                    "old_length": len(old_text),
                    "new_length": len(new_text)
                }
            }

        except PermissionError as e:
            return {
                "success": False,
                "error": f"Permission denied: Cannot write to {file_path}. {str(e)}"
            }
        except UnicodeDecodeError as e:
            return {
                "success": False,
                "error": f"Encoding error: File {file_path} is not valid UTF-8. {str(e)}"
            }
        except Exception as e:
            logger.error(f"Failed to edit {file_path}: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Unexpected error editing {file_path}: {type(e).__name__}: {str(e)}"
            }
