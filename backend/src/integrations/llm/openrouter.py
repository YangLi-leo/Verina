"""OpenRouter LLM provider implementation."""

import json
import logging
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ...core.config import Config
from ...core.exceptions import (
    AuthenticationError,
    InsufficientCreditsError,
    LLMProviderError,
    ModelUnavailableError,
    RateLimitError,
)
from ...core.logging import get_logger
from .base import BaseLLMProvider

logger = get_logger(__name__)


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter implementation of LLM provider.

    OpenRouter provides unified access to multiple AI models through a single API.
    This provider handles authentication, request formatting, and error handling
    for OpenRouter's chat completion endpoint.

    Note: This provider does NOT have a default model. Each caller must specify
    the model explicitly when calling chat() or chat_stream().
    """

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_keys: Optional[List[str]] = None,
    ):
        """Initialize OpenRouter provider.

        Args:
            api_key: Single OpenRouter API key (starts with 'sk-or-').
            api_keys: List of API keys for rotation support.
            If not provided, uses Config.OPENROUTER_API_KEY.
        """
        if api_keys:
            self.api_keys = api_keys
            self.current_key_index = 0
        else:
            single_key = api_key or Config.OPENROUTER_API_KEY
            if not single_key:
                raise ValueError(
                    "OpenRouter API key not provided and OPENROUTER_API_KEY not set"
                )
            self.api_keys = [single_key]
            self.current_key_index = 0

        self._update_headers()

        self._last_stream_usage = None

        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(
                max_connections=100, max_keepalive_connections=20, keepalive_expiry=30
            ),
        )

    def _update_headers(self):
        """Update headers with current API key."""
        current_key = self.api_keys[self.current_key_index]
        self.headers = {
            "Authorization": f"Bearer {current_key}",
            "Content-Type": "application/json",
        }
        if hasattr(self, "client"):
            self.client.headers.update(self.headers)

    def _rotate_api_key(self):
        """Rotate to the next API key."""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self._update_headers()
        logger.info(f"Rotated to API key index {self.current_key_index}")

    def get_last_stream_usage(self) -> Optional[Dict[str, Any]]:
        """Get the usage information from the last stream, if available."""
        return self._last_stream_usage

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close HTTP client."""
        await self.close()

    async def close(self):
        """Close the HTTP client connection pool."""
        if hasattr(self, "client") and self.client:
            await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.RequestError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Send a chat completion request to OpenRouter.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Model to use (e.g.'anthropic/claude-sonnet-4.5'). REQUIRED.
            temperature: Sampling temperature (0.0 to 2.0).
            max_tokens: Maximum tokens in response.
            **kwargs: Additional OpenRouter parameters.

        Returns:
            Raw response from OpenRouter API.

        Raises:
            AuthenticationError: Invalid API key (401).
            InsufficientCreditsError: No credits remaining (402).
            RateLimitError: Too many requests (429).
            ModelUnavailableError: Model is down (502/503).
            LLMProviderError: Other API errors.
        """
        if not model:
            raise ValueError("model parameter is required")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "usage": {"include": True},  # Enable token usage tracking
        }

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        payload.update(kwargs)

        request_id = str(uuid.uuid4())

        try:
            logger.info(
                f"Chat request {request_id}: Starting OpenRouter call with model={model}, "
                f"temperature={temperature}, max_tokens={max_tokens}"
            )

            response = await self.client.post(
                self.BASE_URL,
                json=payload,
                headers=self.headers,  # Use current headers with potentially rotated key
            )

            if response.status_code == 200:
                try:
                    # OpenRouter sometimes returns JSON with leading whitespace
                    # Use strip() to remove it before parsing
                    result = json.loads(response.text.strip())
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    logger.error(f"Response status: {response.status_code}")
                    logger.error(f"Response headers: {response.headers}")
                    logger.error(f"Response length: {len(response.text)} chars")
                    logger.error(f"Response (first 100 chars): {repr(response.text[:100])}")
                    raise Exception(f"OpenRouter returned invalid JSON: {e}")

                usage = result.get("usage", {})

                if usage:
                    prompt_tokens = usage.get('prompt_tokens', 0)
                    completion_tokens = usage.get('completion_tokens', 0)
                    total_tokens = usage.get('total_tokens', 0)

                    prompt_details = usage.get("prompt_tokens_details", {})
                    completion_details = usage.get("completion_tokens_details", {})
                    cached = prompt_details.get("cached_tokens", 0)
                    reasoning_tokens = completion_details.get("reasoning_tokens", 0)

                    cost = usage.get('cost', 0) or 0
                    cost_details = usage.get("cost_details", {}) or {}
                    upstream_cost = cost_details.get("upstream_inference_cost", 0) or 0

                    logger.info(
                        f"💰 USAGE | Prompt: {prompt_tokens} (cached: {cached}) | "
                        f"Completion: {completion_tokens} (reasoning: {reasoning_tokens}) | "
                        f"Total: {total_tokens} | "
                        f"Cost: ${cost:.4f} (upstream: ${upstream_cost:.4f})"
                    )

                    if cached > 0 and prompt_tokens > 0:
                        cache_rate = cached / prompt_tokens * 100
                        logger.info(f"🎯 Cache hit rate: {cache_rate:.1f}% ({cached}/{prompt_tokens} tokens)")

                return result

            error_data = response.json()
            error_info = error_data.get("error", {})
            error_message = error_info.get("message", "Unknown error")
            error_code = error_info.get("code", response.status_code)

            if response.status_code == 401:
                logger.error(f"OpenRouter authentication failed: {error_message}")
                raise AuthenticationError(
                    f"Authentication failed: {error_message}",
                    status_code=401,
                    provider="openrouter",
                )
            elif response.status_code == 402:
                logger.error(f"OpenRouter insufficient credits: {error_message}")
                raise InsufficientCreditsError(
                    f"Insufficient credits: {error_message}",
                    status_code=402,
                    provider="openrouter",
                )
            elif response.status_code == 429:
                logger.warning(f"OpenRouter rate limit exceeded: {error_message}")
                raise RateLimitError(
                    f"Rate limit exceeded: {error_message}",
                    status_code=429,
                    provider="openrouter",
                )
            elif response.status_code in [502, 503]:
                logger.error(
                    f"OpenRouter model unavailable ({response.status_code}): {error_message}"
                )
                raise ModelUnavailableError(
                    f"Model unavailable: {error_message}",
                    status_code=response.status_code,
                    provider="openrouter",
                )
            else:
                logger.error(
                    f"OpenRouter API error {response.status_code}: {error_message}"
                )
                raise LLMProviderError(
                    f"OpenRouter API error: {error_message}",
                    status_code=response.status_code,
                    provider="openrouter",
                )

        except httpx.TimeoutException:
            logger.error(
                f"OpenRouter request timed out for model: {model}"
            )
            raise LLMProviderError(
                "Request timed out after 30 seconds",
                status_code=408,
                provider="openrouter",
            )
        except httpx.RequestError as e:
            logger.error(f"Network error calling OpenRouter: {str(e)}")
            raise LLMProviderError(f"Network error: {str(e)}", provider="openrouter")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.RequestError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream chat completion from OpenRouter.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Model to use (e.g.'anthropic/claude-sonnet-4.5'). REQUIRED.
            temperature: Sampling temperature (0.0 to 2.0).
            max_tokens: Maximum tokens in response.
            **kwargs: Additional OpenRouter parameters.

        Yields:
            Content chunks as they arrive from the model.

        Raises:
            Same exceptions as chat() method.
        """
        if not model:
            raise ValueError("model parameter is required")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            "usage": {"include": True},  # Enable token usage tracking
        }

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        payload.update(kwargs)

        request_id = str(uuid.uuid4())

        try:
            logger.info(
                f"Chat stream request {request_id}: Starting OpenRouter streaming with model={model}"
            )

            async with self.client.stream(
                "POST", self.BASE_URL, json=payload, headers=self.headers
            ) as response:

                if response.status_code != 200:
                    error_data = await response.aread()
                    try:
                        error_json = json.loads(error_data.decode())
                        error_info = error_json.get("error", {})
                        error_message = error_info.get("message", "Unknown error")
                    except:
                        error_message = f"HTTP {response.status_code}"

                    if response.status_code == 401:
                        raise AuthenticationError(
                            f"Authentication failed: {error_message}",
                            status_code=401,
                            provider="openrouter",
                        )
                    elif response.status_code == 402:
                        raise InsufficientCreditsError(
                            f"Insufficient credits: {error_message}",
                            status_code=402,
                            provider="openrouter",
                        )
                    elif response.status_code == 429:
                        raise RateLimitError(
                            f"Rate limit exceeded: {error_message}",
                            status_code=429,
                            provider="openrouter",
                        )
                    elif response.status_code in [502, 503]:
                        raise ModelUnavailableError(
                            f"Model unavailable: {error_message}",
                            status_code=response.status_code,
                            provider="openrouter",
                        )
                    else:
                        raise LLMProviderError(
                            f"OpenRouter API error: {error_message}",
                            status_code=response.status_code,
                            provider="openrouter",
                        )

                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()

                        if line.startswith("data: "):
                            data = line[6:]  # Remove 'data: ' prefix

                            if data == "[DONE]":
                                logger.info(f"Stream request {request_id}: Completed")
                                return

                            try:
                                data_obj = json.loads(data)

                                if "usage" in data_obj:
                                    usage = data_obj["usage"]

                                    prompt_tokens = usage.get('prompt_tokens', 0)
                                    completion_tokens = usage.get('completion_tokens', 0)
                                    total_tokens = usage.get('total_tokens', 0)

                                    prompt_details = usage.get("prompt_tokens_details", {})
                                    completion_details = usage.get("completion_tokens_details", {})
                                    cached = prompt_details.get("cached_tokens", 0)
                                    reasoning_tokens = completion_details.get("reasoning_tokens", 0)

                                    cost = usage.get('cost', 0) or 0
                                    cost_details = usage.get("cost_details", {}) or {}
                                    upstream_cost = cost_details.get("upstream_inference_cost", 0) or 0

                                    logger.info(
                                        f"💰 USAGE (stream) | Prompt: {prompt_tokens} (cached: {cached}) | "
                                        f"Completion: {completion_tokens} (reasoning: {reasoning_tokens}) | "
                                        f"Total: {total_tokens} | "
                                        f"Cost: ${cost:.4f} (upstream: ${upstream_cost:.4f})"
                                    )

                                    self._last_stream_usage = usage

                                content = (
                                    data_obj.get("choices", [{}])[0]
                                    .get("delta", {})
                                    .get("content")
                                )
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                pass

        except httpx.TimeoutException:
            logger.error(
                f"OpenRouter stream request timed out for model: {model}"
            )
            raise LLMProviderError(
                "Request timed out after 30 seconds",
                status_code=408,
                provider="openrouter",
            )
        except httpx.RequestError as e:
            logger.error(f"Network error calling OpenRouter stream: {str(e)}")
            raise LLMProviderError(f"Network error: {str(e)}", provider="openrouter")
