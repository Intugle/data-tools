import os
import anthropic
from core.llms.base import LLMFactory
from ..exceptions import MissingApiKeyError

class ClaudeClientFactory(LLMFactory):
    def get_llm(self) -> anthropic.Anthropic:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
           raise MissingApiKeyError("Missing environment variable: CLAUDE_API_KEY")
        
        return anthropic.Anthropic(api_key=api_key)
