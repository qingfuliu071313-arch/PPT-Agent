"""LLM provider abstraction layer."""

from ppt_agent.llm.base import BaseLLM
from ppt_agent.llm.claude_llm import ClaudeLLM
from ppt_agent.llm.gemini_llm import GeminiLLM
from ppt_agent.llm.deepseek_llm import DeepseekLLM


def create_llm(provider: str, **kwargs) -> BaseLLM:
    providers = {
        "claude": ClaudeLLM,
        "gemini": GeminiLLM,
        "deepseek": DeepseekLLM,
    }
    if provider not in providers:
        raise ValueError(f"Unknown provider: {provider}. Choose from: {list(providers.keys())}")
    return providers[provider](**kwargs)


__all__ = ["BaseLLM", "ClaudeLLM", "GeminiLLM", "DeepseekLLM", "create_llm"]
