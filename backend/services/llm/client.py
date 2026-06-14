"""LLM client factory.

Returns an AsyncOpenAI client configured for the requested provider.
DeepSeek and Gemini both expose OpenAI-compatible REST endpoints, so the same
client works for all three — only the base_url and api_key differ.

Adding a new provider: add one entry to _PROVIDER_BASE_URLS.
"""
from openai import AsyncOpenAI

_PROVIDER_BASE_URLS: dict = {
    "deepseek": "https://api.deepseek.com",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
}


def make_llm_client(provider: str, api_key: str) -> AsyncOpenAI:
    """Return an AsyncOpenAI client for the given provider."""
    base_url = _PROVIDER_BASE_URLS.get(provider)
    return AsyncOpenAI(api_key=api_key, base_url=base_url)
