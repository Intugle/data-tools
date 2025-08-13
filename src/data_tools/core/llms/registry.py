import os
from enum import Enum
from typing import Type

from .base import LLMFactory
from .exceptions import ProviderNotFoundError
from .types.openai_factory import OpenAIClientFactory
from .types.azure_openai_factory import AzureOpenAIClientFactory
from .types.claude_factory import ClaudeClientFactory


class LLMProvider(str, Enum):
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    CLAUDE = "claude"


_PROVIDER_MAP: dict[LLMProvider, Type[LLMFactory]] = {
    LLMProvider.OPENAI: OpenAIClientFactory,
    LLMProvider.AZURE_OPENAI: AzureOpenAIClientFactory,
    LLMProvider.CLAUDE: ClaudeClientFactory
}


def get_llm_factory(provider: str | None = None) -> LLMFactory:
    """
    Returns the appropriate LLMFactory subclass instance.
    """
    provider_str = (provider or os.getenv("LLM_PROVIDER", "")).lower()

    try:
        provider_enum = LLMProvider(provider_str)
    except ValueError:
        raise ProviderNotFoundError(provider_str, [p.value for p in LLMProvider])

    factory_cls = _PROVIDER_MAP[provider_enum]
    return factory_cls()
