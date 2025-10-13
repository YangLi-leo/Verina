"""Chat system configuration - Chat-specific settings only.

For data storage paths, use src.core.config.Config.DATA_BASE_DIR
"""


class ChatConfig:
    """Configuration for ChatAgent.

    Note: For data storage paths, import from src.core.config.Config
    """

    # Model settings
    DEFAULT_MODEL: str = "openai/gpt-5-codex"

    # ReAct loop
    MAX_ITERATIONS: int = 200

    # Context management
    CONTEXT_LIMIT: int = 400000
    AUTO_COMPACT_THRESHOLD: int = 280000
