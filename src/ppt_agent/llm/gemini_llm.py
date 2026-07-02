"""Google Gemini LLM provider."""

from __future__ import annotations

from google import genai
from ppt_agent.llm.base import BaseLLM, LLMResponseError


class GeminiLLM(BaseLLM):

    def __init__(self, api_key: str = "", model: str = "gemini-2.5-flash"):
        self.client = genai.Client(
            api_key=api_key or None,
            http_options={"timeout": 120_000},  # milliseconds
        )
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
        text = response.text  # None when safety-blocked or finished empty
        if not text:
            raise LLMResponseError("Gemini returned an empty response (possibly safety-blocked)")
        return text
