"""AEGIS AI — LLM Provider Registry and Factory
"""

import logging
import os

from backend.ai.base import BaseLLMProvider
from backend.ai.providers.gemini_provider import GeminiLLMProvider
from backend.ai.providers.mock_provider import MockLLMProvider
from backend.core.config import settings

logger = logging.getLogger("aegis.ai.providers")

# Models that explicitly map to the mock/deterministic provider
_MOCK_MODEL_NAMES = {"mock-aegis-core", "mock", "test", "deterministic"}


def get_llm_provider(provider_type: str | None = None, model_name: str | None = None) -> BaseLLMProvider:
    """Factory function returning the active LLM provider instance.
    
    Model name routing:
    - If model_name is a known mock identifier → MockLLMProvider
    - If model_name is a known Gemini model (gemini-*) → GeminiLLMProvider
    - Otherwise, fall back to configured provider (settings.LLM_PROVIDER)
    """
    model = model_name or settings.LLM_MODEL

    # --- Explicit mock route ---
    if model and model.lower() in _MOCK_MODEL_NAMES:
        return MockLLMProvider(model_name=model)

    if settings.APP_ENV == "testing":
        return MockLLMProvider(model_name=model or "mock-aegis-core")

    # --- Determine effective provider ---
    provider = provider_type or settings.LLM_PROVIDER

    # If model name is explicitly a Gemini model, force Gemini provider
    if model and model.lower().startswith("gemini"):
        provider = "gemini"

    if provider.lower() in ("mock", "test"):
        return MockLLMProvider(model_name=model or "mock-aegis-core")

    if provider.lower() == "gemini":
        api_key = (
            settings.LLM_API_KEY
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        # Validate that the API key is not a placeholder
        if api_key and api_key not in ("YOUR_GEMINI_API_KEY_HERE", ""):
            try:
                return GeminiLLMProvider(model_name=model, api_key=api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini provider: {e}. Falling back to MockLLMProvider.")
        else:
            logger.info("No valid Gemini API key detected. Using MockLLMProvider.")

    return MockLLMProvider(model_name=model or "mock-aegis-core")


__all__ = ["BaseLLMProvider", "GeminiLLMProvider", "MockLLMProvider", "get_llm_provider"]
