import os
from openai import AzureOpenAI
from core.llms.base import LLMFactory
from ..exceptions import MissingApiKeyError

class AzureOpenAIClientFactory(LLMFactory):
    def get_llm(self) -> AzureOpenAI:
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

        if not api_key:
            raise MissingApiKeyError("Missing environment variable: AZURE_OPENAI_API_KEY")
        if not endpoint:
            raise MissingApiKeyError("Missing environment variable: AZURE_OPENAI_ENDPOINT")

        return AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version
        )
