import os
from openai import OpenAI
from core.llms.base import LLMFactory
from ..exceptions import MissingApiKeyError

class OpenAIClientFactory(LLMFactory):
    def get_llm(self) -> OpenAI:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise MissingApiKeyError("Missing environment variable: OPENAI_API_KEY")
        
        return OpenAI(api_key=api_key)
