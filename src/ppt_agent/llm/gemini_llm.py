"""Google Gemini LLM provider."""

from __future__ import annotations

from google import genai
from ppt_agent.llm.base import BaseLLM


class GeminiLLM(BaseLLM):

    def __init__(self, api_key: str = "", model: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key or None)
        self.model = model

    def generate(self, prompt: str, system: str = "") -> str:
        config = {}
        if system:
            config["system_instruction"] = system
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        return response.text

    def generate_json(self, prompt: str, system: str = "") -> dict:
        full_prompt = prompt + "\n\nRespond with valid JSON only, no markdown fences."
        text = self.generate(full_prompt, system)
        return self._extract_json(text)
