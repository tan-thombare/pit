"""Providers package exports and factory.

The primary provider is GenericHTTPProvider which handles any AI application endpoint.
OpenAI/Anthropic providers are used when the config was populated by a provider preset.
"""

from pit.config.models import APIConfig, ProviderType
from pit.providers.base import ConnectionTestResult, LLMProvider, LLMResponse
from pit.providers.openai import OpenAIProvider
from pit.providers.anthropic import AnthropicProvider
from pit.providers.generic import GenericHTTPProvider


def create_provider(config: APIConfig) -> LLMProvider:
    """Create and return an LLM provider instance matching the given configuration.

    The default is GenericHTTPProvider (works for any HTTP endpoint).
    OpenAI/Anthropic providers are used only when a specific provider preset is active
    and base_url is set (i.e. the user explicitly chose those preset paths).
    """
    match config.provider:
        case ProviderType.OPENAI | ProviderType.OPENAI_COMPATIBLE:
            return OpenAIProvider(config)
        case ProviderType.ANTHROPIC:
            return AnthropicProvider(config)
        case _:
            # Default: generic HTTP provider for custom AI application endpoints
            return GenericHTTPProvider(config)


__all__ = [
    "LLMProvider",
    "LLMResponse",
    "ConnectionTestResult",
    "OpenAIProvider",
    "AnthropicProvider",
    "GenericHTTPProvider",
    "create_provider",
]
