"""Centralized configuration management for the application."""

import os
from pathlib import Path
from typing import Optional

# Load environment variables from config directory
try:
    from dotenv import load_dotenv

    project_root = Path(__file__).parent.parent.parent.parent
    config_dir = project_root / "config"

    env_name = os.getenv("NODE_ENV", "development")
    env_file = config_dir / f".env.{env_name}"

    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded config from: {env_file}")
    else:
        print(f"Warning: Config file {env_file} not found")

except ImportError:
    print(
        "Warning: python-dotenv not installed, using system environment variables only"
    )


class Config:
    """Unified configuration management for API keys and environment settings.

    This class provides centralized access to all configuration values,
    with validation to ensure required settings are present.
    """

    # Application Settings
    NODE_ENV: str = os.getenv("NODE_ENV", "development")
    PORT: int = int(os.getenv("PORT", "3000"))
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # URLs
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # API Keys
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

    # API Keys - Search Providers
    EXA_API_KEY: str = os.getenv("EXA_API_KEY", "")  # Primary neural search engine

    # Environment Configuration
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Performance Settings
    MAX_SEARCH_ROUNDS: int = int(os.getenv("MAX_SEARCH_ROUNDS", "3"))
    RESPONSE_TIMEOUT: int = int(os.getenv("RESPONSE_TIMEOUT", "30"))

    # Userspace Settings
    USERSPACE_DIR: str = os.getenv("USERSPACE_DIR", "src/userspace")

    # Data Storage
    DATA_BASE_DIR: str = os.getenv("DATA_BASE_DIR", "/app/data")

    # Authentication
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    SESSION_SECRET: str = os.getenv("SESSION_SECRET", "")

    # Rate Limiting
    RATE_LIMIT_WINDOW: str = os.getenv("RATE_LIMIT_WINDOW", "15m")
    RATE_LIMIT_MAX_REQUESTS: int = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "100"))

    # Feature Flags
    ENABLE_CHAT_MODE: bool = os.getenv("ENABLE_CHAT_MODE", "true").lower() == "true"
    ENABLE_DEEP_SEARCH: bool = os.getenv("ENABLE_DEEP_SEARCH", "true").lower() == "true"
    ENABLE_USER_ANALYTICS: bool = (
        os.getenv("ENABLE_USER_ANALYTICS", "true").lower() == "true"
    )

    # User Profile Configuration
    PROFILE_UPDATE_THRESHOLD: int = int(os.getenv("PROFILE_UPDATE_THRESHOLD", "10"))
    PROFILE_ANALYSIS_MODEL: str = os.getenv(
        "PROFILE_ANALYSIS_MODEL", ""
    )  # User should specify
    ENABLE_USER_MEMORY: bool = (
        os.getenv("ENABLE_USER_MEMORY", "false").lower() == "true"
    )

    # E2B Sandbox Configuration
    E2B_API_KEY: str = os.getenv("E2B_API_KEY", "")  # Required for code execution

    @classmethod
    def validate(cls) -> None:
        """Validate that all required configuration values are present.

        Raises:
            ValueError: If any required configuration is missing.
        """
        if cls.ENVIRONMENT.lower() == "production":
            if not cls.OPENROUTER_API_KEY:
                raise ValueError("OPENROUTER_API_KEY is required in production")
            if not cls.EXA_API_KEY:
                raise ValueError("EXA_API_KEY is required in production")

        if cls.ENVIRONMENT not in ["development", "staging", "production"]:
            raise ValueError(f"Invalid ENVIRONMENT: {cls.ENVIRONMENT}")

        if cls.MAX_SEARCH_ROUNDS < 1 or cls.MAX_SEARCH_ROUNDS > 10:
            raise ValueError(
                f"MAX_SEARCH_ROUNDS must be between 1 and 10, got {cls.MAX_SEARCH_ROUNDS}"
            )

        if cls.RESPONSE_TIMEOUT < 5 or cls.RESPONSE_TIMEOUT > 300:
            raise ValueError(
                f"RESPONSE_TIMEOUT must be between 5 and 300 seconds, got {cls.RESPONSE_TIMEOUT}"
            )

    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production environment."""
        return cls.ENVIRONMENT == "production"

    @classmethod
    def is_development(cls) -> bool:
        """Check if running in development environment."""
        return cls.ENVIRONMENT == "development"

    @classmethod
    def has_e2b_key(cls) -> bool:
        """Check if E2B API key is configured for code execution.

        Returns:
            True if E2B_API_KEY is set and non-empty, False otherwise.
        """
        return bool(cls.E2B_API_KEY and cls.E2B_API_KEY.strip())
