"""Generic LLM client separated from service logic.

This module centralizes all language model interactions so that
other services (email, chat, etc.) can use the same interface.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMClient:
    """Simple LLM client abstraction.

    A real implementation would call an external LLM service.
    For testing purposes we provide a deterministic stub.
    """

    provider: Optional[str] = None

    def generate(self, prompt: str) -> str:
        """Generate text for the given prompt.

        The default stub just echoes the prompt to keep tests deterministic.
        """
        return f"LLM response to: {prompt}"

    def summarize(self, text: str, max_sentences: int = 2) -> str:
        """Return a naive summary of ``text``.

        This helper splits the text on periods and returns the first
        ``max_sentences`` sentences. It acts as a lightweight summary
        function that mimics an LLM call but keeps unit tests simple.
        """
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        summary = '. '.join(sentences[:max_sentences])
        if summary and not summary.endswith('.'):
            summary += '.'
        return summary
