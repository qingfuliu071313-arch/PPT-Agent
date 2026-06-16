"""Deepseek LLM provider (OpenAI-compatible API)."""

from __future__ import annotations

from openai import OpenAI
from ppt_agent.llm.base import BaseLLM


class DeepseekLLM(BaseLLM):

    def __init__(self, api_key: str = "", model: str = "deepseek-chat"):
        self.model = model
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1",
        )

    def generate(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=8192,
        )
        return response.choices[0].message.content

    def generate_json(self, prompt: str, system: str = "") -> dict:
        full_prompt = prompt + "\n\nRespond with valid JSON only, no markdown fences."
        text = self.generate(full_prompt, system)
        return self._extract_json(text)
