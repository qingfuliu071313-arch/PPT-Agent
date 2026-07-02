"""Deepseek LLM provider (OpenAI-compatible API)."""

from __future__ import annotations

from openai import OpenAI
from ppt_agent.llm.base import BaseLLM, LLMResponseError


class DeepseekLLM(BaseLLM):

    def __init__(self, api_key: str = "", model: str = "deepseek-chat"):
        self.model = model
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1",
            timeout=120.0,
        )

    def generate(self, prompt: str, system: str = "") -> str:
        return self._chat(prompt, system)

    def _generate_for_json(self, prompt: str, system: str) -> str:
        # DeepSeek's OpenAI-compatible JSON mode guarantees syntactically valid JSON
        return self._chat(prompt, system, response_format={"type": "json_object"})

    def _chat(self, prompt: str, system: str, **extra) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=8192,
            **extra,
        )
        content = response.choices[0].message.content
        if not content:
            raise LLMResponseError("DeepSeek returned an empty response")
        return content
