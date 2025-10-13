"""File List Tool - List all files in workspace."""

import logging
import shutil
from pathlib import Path
from typing import Any, Dict

from .base import BaseTool

logger = logging.getLogger(__name__)


class FileListTool(BaseTool):
    """List all files in workspace."""

    def __init__(self, workspace_dir: Path):
        """Initialize with workspace directory.

        Args:
            workspace_dir: Path object for the session workspace directory.
        """
        self.workspace = workspace_dir

    @property
    def name(self) -> str:
        return "file_list"

    @property
    def description(self) -> str:
        return (
            "List all files in the workspace. "
            "Use this to see what files you've created and their sizes."
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """List all files in workspace.

        Returns:
            List of files with names and sizes
        """
        try:
            if not self.workspace.exists():
                return {
                    "success": True,
                    "files": [],
                    "count": 0,
                    "message": "Workspace is empty"
                }

            files = []

            # Walk through all files in workspace
            for file_path in self.workspace.rglob("*"):
                if file_path.is_file():
                    # Get relative path from workspace
                    rel_path = file_path.relative_to(self.workspace)
                    size = file_path.stat().st_size

                    files.append({
                        "name": str(rel_path),
                        "size": size
                    })

            # Sort by name
            files.sort(key=lambda x: x["name"])

            if not files:
                return {
                    "success": True,
                    "files": [],
                    "count": 0,
                    "message": "Workspace is empty"
                }

            return {
                "success": True,
                "files": files,
                "count": len(files),
                "workspace": str(self.workspace),
                "message": f"Found {len(files)} file(s) in workspace"
            }

        except Exception as e:
            logger.error(f"File list error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def cleanup(self):
        """Cleanup workspace - delete all files and directory."""
        if self.workspace.exists():
            try:
                shutil.rmtree(self.workspace)
                logger.info(f"Cleaned up workspace: {self.workspace}")
            except Exception as e:
                logger.error(f"Failed to cleanup workspace: {e}", exc_info=True)
