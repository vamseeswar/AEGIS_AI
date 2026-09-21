"""AEGIS AI — Google Gemini LLM Provider
Implements native streaming and generation using the new Google Gen AI SDK (google-genai).
"""

import os
from collections.abc import AsyncGenerator

from backend.ai.base import BaseLLMProvider
from backend.core.config import settings

try:
    from google import genai
    from google.genai import types as genai_types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False


class GeminiLLMProvider(BaseLLMProvider):
    """Google Gemini model provider using the new google-genai SDK with async streaming support."""

    def __init__(self, model_name: str | None = None, api_key: str | None = None):
        super().__init__(model_name=model_name or settings.LLM_MODEL)
        self.api_key = (
            api_key
            or settings.LLM_API_KEY
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )

        if not _GENAI_AVAILABLE:
            raise RuntimeError("google-genai package is not installed. Run: pip install google-genai")

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY must be provided for Gemini provider.")

        # Validate it's not a placeholder
        if self.api_key in ("YOUR_GEMINI_API_KEY_HERE", ""):
            raise ValueError("GEMINI_API_KEY is still set to placeholder. Please set a real API key.")

        self._client = genai.Client(api_key=self.api_key)

    def _build_contents_and_config(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> tuple[str | None, list, object]:
        """Separates system prompt from conversation history and formats for Gemini genai SDK."""
        system_instruction: str | None = None
        contents = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                if system_instruction is None:
                    system_instruction = content
                else:
                    system_instruction += "\n\n" + content
            elif role == "assistant":
                contents.append(
                    genai_types.Content(role="model", parts=[genai_types.Part(text=content)])
                )
            else:
                contents.append(
                    genai_types.Content(role="user", parts=[genai_types.Part(text=content)])
                )

        generation_config = genai_types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_instruction,
        )

        return system_instruction, contents, generation_config

    async def generate_response(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> str:
        import asyncio
        _, contents, config = self._build_contents_and_config(messages, temperature, max_tokens)

        response = await asyncio.to_thread(
            self._client.models.generate_content,
            model=self.model_name,
            contents=contents,
            config=config,
        )
        return response.text or ""

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        import asyncio
        _, contents, config = self._build_contents_and_config(messages, temperature, max_tokens)

        # Run streaming in a thread to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        def _stream_sync():
            try:
                for chunk in self._client.models.generate_content_stream(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                ):
                    if chunk.text:
                        loop.call_soon_threadsafe(queue.put_nowait, chunk.text)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        asyncio.ensure_future(asyncio.to_thread(_stream_sync))

        while True:
            token = await queue.get()
            if token is None:
                break
            yield token
