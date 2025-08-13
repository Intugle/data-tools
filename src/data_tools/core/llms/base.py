from abc import ABC, abstractmethod
from typing import Any


class LLMFactory(ABC):
    """
    Abstract base for all LLM provider factories.
    """

    @abstractmethod
    def get_llm(self) -> Any:
        """
        Returns an instantiated LLM client.
        """
        pass
