"""Extractors subpackage for NLP backends."""

from intugle.text_processor.extractors.base import BaseExtractor
from intugle.text_processor.extractors.llm_extractor import LLMExtractor

__all__ = ["BaseExtractor", "LLMExtractor"]
