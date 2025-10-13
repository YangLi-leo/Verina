"""Base interface for LLM providers."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.

    All LLM providers (OpenRouter, Together AI, etc.) must implement this interface.
    This ensures consistent behavior across different providers.
    """

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Send a chat completion request to the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            Following OpenAI format for compatibility.
            model: Optional model override. If not provided, uses provider default.
            temperature: Sampling temperature (0.0 to 2.0). Higher = more creative.
            max_tokens: Maximum tokens in response. None = model default.
            **kwargs: Additional provider-specific parameters.

        Returns:
            Raw response dict from the provider. Structure may vary by provider
            but should include at minimum:
            - 'choices': List with at least one choice
            - 'usage': Token usage information

        Raises:
            LLMProviderError: If the request fails for any reason.
        """
        pass
   