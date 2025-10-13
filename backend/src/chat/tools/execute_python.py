from typing import Any, Dict, Optional, List
import json
import logging
import base64
from pathlib import Path
from datetime import datetime
from e2b_code_interpreter import Sandbox
from src.core.config import Config
from .base import BaseTool

logger = logging.getLogger(__name__)


class SandboxTool(BaseTool):
    """Sandbox tool for executing Python code in a secure E2B environment.

    Features:
    - Execute calculations and data analysis
    - Summarize data with statistics
    - Generate visualizations (matplotlib, seaborn, plotly)
    - Persistent state within a ReAct loop (variables preserved across calls)
    - Save all outputs to workspace/analysis/ directory
      • Images: analysis/images/ (png, jpeg, svg)
      • Data: analysis/data/ (csv, json, txt)
      • Reports: analysis/reports/ (pdf, html, markdown)

    The sandbox is created on first use and reused for subsequent calls
    within the same ReAct loop, allowing multi-step data analysis.
    """

    # Execution timeout (10 minutes)
    EXECUTION_TIMEOUT = 600

    def __init__(self, workspace_dir: Optional[Path] = None):
        self.api_key = Config.E2B_API_KEY
        if not self.api_key:
            logger.warning("E2B_API_KEY not configured - SandboxTool will fail at runtime")

        self._sandbox: Optional[Sandbox] = None

        self.workspace_dir = workspace_dir

        if self.workspace_dir:
            self._init_analysis_dirs()

    @property
    def name(self) -> str:
        return "execute_python"

    @property
    def description(self) -> str:
        return (
            "Execute Python code in a secure sandbox for data analysis and visualization. "
            "\n\n"
            "📊 Output Storage:\n"
            "  • Images (PNG/JPEG/SVG) → analysis/images/plot_NNN.{ext}\n"
            "  • Data (JSON/CSV) → analysis/data/output_NNN.{ext}\n"
            "  • Reports (HTML/PDF/Markdown) → analysis/reports/report_NNN.{ext}\n"
            "\n"
            "⚠️ IMPORTANT for High-Quality Results:\n"
            "To generate professional, publication-ready visualizations, you must provide DETAILED and COMPLETE code. "
            "Think step by step about what makes a visualization clear and informative. "
            "Simple or rushed code produces poor results. Invest effort in writing thorough code for excellent output.\n"
            "\n"
            "📦 Available: numpy, pandas, matplotlib, seaborn, plotly, scipy, sklearn\n"
            "🔄 Variables persist across calls within the same conversation\n"
            "💾 Returns: {success, output, files_generated: [{path, type, size_kb}], execution_time}"
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The python code to execute in a single cell"
                }
            },
            "required": ["code"]
        }

    def _init_analysis_dirs(self) -> None:
        """Initialize analysis output directories."""
        if not self.workspace_dir:
            return

        analysis_dir = self.workspace_dir / "analysis"
        (analysis_dir / "images").mkdir(parents=True, exist_ok=True)
        (analysis_dir / "data").mkdir(parents=True, exist_ok=True)
        (analysis_dir / "reports").mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized analysis directories at {analysis_dir}")

    def _get_or_create_sandbox(self) -> Sandbox:
        """Get existing sandbox or create new one for this ReAct session."""
        if self._sandbox is None:
            logger.info("Creating new E2B sandbox for this session")
            self._sandbox = Sandbox.create(api_key=self.api_key, timeout=self.EXECUTION_TIMEOUT)
        return self._sandbox

    def _get_next_sequence(self, directory: Path, prefix: str) -> int:
        """Get next sequence number for files with given prefix."""
        if not directory.exists():
            return 1

        max_num = 0
        for file in directory.iterdir():
            if file.stem.startswith(prefix):
                try:
                    num_str = file.stem.split('_')[-1]
                    num = int(num_str)
                    max_num = max(max_num, num)
                except (ValueError, IndexError):
                    continue

        return max_num + 1

    def _save_image(self, base64_data: str, extension: str) -> Optional[Dict[str, Any]]:
        """Save image to workspace/analysis/images/ and return file info."""
        if not self.workspace_dir:
            return None

        images_dir = self.workspace_dir / "analysis" / "images"
        seq = self._get_next_sequence(images_dir, "plot")
        filename = f"plot_{seq:03d}.{extension}"
        filepath = images_dir / filename

        image_data = base64.b64decode(base64_data)
        filepath.write_bytes(image_data)

        relative_path = f"analysis/images/{filename}"
        logger.info(f"Saved {extension.upper()} image to {relative_path}")

        return {
            "path": relative_path,
            "type": f"image/{extension}",
            "size_kb": round(len(image_data) / 1024, 2)
        }

    def _save_data(self, content: str, extension: str) -> Optional[Dict[str, Any]]:
        """Save data file to workspace/analysis/data/ and return file info."""
        if not self.workspace_dir:
            return None

        data_dir = self.workspace_dir / "analysis" / "data"
        seq = self._get_next_sequence(data_dir, "output")
        filename = f"output_{seq:03d}.{extension}"
        filepath = data_dir / filename

        filepath.write_text(content, encoding="utf-8")

        relative_path = f"analysis/data/{filename}"
        logger.info(f"Saved {extension.upper()} data to {relative_path}")

        return {
            "path": relative_path,
            "type": f"data/{extension}",
            "size_kb": round(len(content.encode('utf-8')) / 1024, 2)
        }

    def _save_report(self, content: str, extension: str) -> Optional[Dict[str, Any]]:
        """Save report to workspace/analysis/reports/ and return file info."""
        if not self.workspace_dir:
            return None

        reports_dir = self.workspace_dir / "analysis" / "reports"
        seq = self._get_next_sequence(reports_dir, "report")
        filename = f"report_{seq:03d}.{extension}"
        filepath = reports_dir / filename

        if extension == "pdf":
            pdf_data = base64.b64decode(content)
            filepath.write_bytes(pdf_data)
            size_kb = round(len(pdf_data) / 1024, 2)
        else:
            filepath.write_text(content, encoding="utf-8")
            size_kb = round(len(content.encode('utf-8')) / 1024, 2)

        relative_path = f"analysis/reports/{filename}"
        logger.info(f"Saved {extension.upper()} report to {relative_path}")

        return {
            "path": relative_path,
            "type": f"report/{extension}",
            "size_kb": size_kb
        }

    async def execute(self, code: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute Python code in E2B sandbox.

        Args:
            code: Python code to execute

        Returns:
            Dict containing:
            - success: bool
            - output: Text output from execution
            - files_generated: List of file info dicts with path, type, size_kb
            - execution_time: Execution time in seconds
            - error: Error message if failed
        """
        if not self.api_key:
            error_msg = "E2B_API_KEY not configured. Please set it in your environment."
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        import time
        start_time = time.time()

        try:
            logger.info(f"Executing Python code:\n{code[:200]}...")

            sandbox = self._get_or_create_sandbox()

            execution = sandbox.run_code(code)

            text_outputs = []
            files_generated = []

            if execution.text:
                text_outputs.append(execution.text)

            if execution.results:
                for idx, result in enumerate(execution.results):
                    if result.png:
                        logger.info(f"Result {idx}: PNG image ({len(result.png)} chars base64)")
                        file_info = self._save_image(result.png, "png")
                        if file_info:
                            files_generated.append(file_info)
                            text_outputs.append(f"📊 Generated: {file_info['path']}")

                    if result.jpeg:
                        logger.info(f"Result {idx}: JPEG image")
                        file_info = self._save_image(result.jpeg, "jpeg")
                        if file_info:
                            files_generated.append(file_info)
                            text_outputs.append(f"📊 Generated: {file_info['path']}")

                    if result.svg:
                        logger.info(f"Result {idx}: SVG image")
                        file_info = self._save_data(result.svg, "svg")
                        if file_info:
                            files_generated.append(file_info)
                            text_outputs.append(f"📊 Generated: {file_info['path']}")

                    if result.pdf:
                        logger.info(f"Result {idx}: PDF document")
                        file_info = self._save_report(result.pdf, "pdf")
                        if file_info:
                            files_generated.append(file_info)
                            text_outputs.append(f"📄 Generated: {file_info['path']}")

                    if result.html:
                        logger.info(f"Result {idx}: HTML document")
                        file_info = self._save_report(result.html, "html")
                        if file_info:
                            files_generated.append(file_info)
                            text_outputs.append(f"📄 Generated: {file_info['path']}")

                    if result.markdown:
                        logger.info(f"Result {idx}: Markdown document")
                        file_info = self._save_report(result.markdown, "md")
                        if file_info:
                            files_generated.append(file_info)
                            text_outputs.append(f"📄 Generated: {file_info['path']}")

                    if result.json:
                        logger.info(f"Result {idx}: JSON data")
                        json_str = json.dumps(result.json, indent=2)
                        file_info = self._save_data(json_str, "json")
                        if file_info:
                            files_generated.append(file_info)
                            text_outputs.append(f"📦 Generated: {file_info['path']}")

                    if result.text and result.text not in text_outputs:
                        text_outputs.append(result.text)

                    if result.chart:
                        logger.info(f"Result {idx}: Chart metadata detected")
                        chart_info = [f"\n📈 Chart generated"]

                        if hasattr(result.chart, 'type'):
                            chart_info.append(f"   Type: {result.chart.type}")
                        if hasattr(result.chart, 'title') and result.chart.title:
                            chart_info.append(f"   Title: {result.chart.title}")
                        if hasattr(result.chart, 'elements'):
                            chart_info.append(f"   Data points: {len(result.chart.elements)}")

                        text_outputs.append("\n".join(chart_info))

            execution_time = time.time() - start_time

            output_text = "\n\n".join(text_outputs) if text_outputs else "Code executed successfully (no output)"

            result_dict = {
                "success": True,
                "output": output_text,
                "files_generated": files_generated,
                "execution_time": round(execution_time, 2)
            }

            logger.info(f"Execution completed in {execution_time:.2f}s, generated {len(files_generated)} files")
            return result_dict

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Sandbox execution failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "output": "",
                "files_generated": [],
                "error": error_msg,
                "execution_time": round(execution_time, 2)
            }

    def cleanup(self):
        """Cleanup sandbox when ReAct loop ends.

        This should be called by ChatAgent after the conversation completes.
        """
        if self._sandbox:
            try:
                logger.info("Cleaning up E2B sandbox")
                self._sandbox.kill()
                self._sandbox = None
            except Exception as e:
                logger.error(f"Failed to cleanup sandbox: {e}", exc_info=True)
