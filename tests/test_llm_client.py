import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from llm import LLMClient


def test_summarize_returns_first_sentences():
    client = LLMClient()
    text = (
        "This is the first sentence. This is the second sentence. "
        "And this would be the third one."
    )
    summary = client.summarize(text, max_sentences=2)
    assert summary == "This is the first sentence. This is the second sentence."


def test_generate_echoes_prompt():
    client = LLMClient()
    prompt = "Hello there"
    assert client.generate(prompt) == f"LLM response to: {prompt}"
