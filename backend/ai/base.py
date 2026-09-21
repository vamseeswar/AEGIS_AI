"""AEGIS AI — Base LLM Provider Interface
Defines the standard contract for conversational AI model providers.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers (Gemini, OpenAI, Mock)."""

    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    async def generate_response(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> str:
        """Generates a non-streaming completion for the given conversation messages."""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Streams incremental text tokens for the given conversation messages."""
        pass
