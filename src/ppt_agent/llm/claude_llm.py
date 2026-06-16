"""Claude (Anthropic) LLM provider."""

from __future__ import annotations

import anthropic
from ppt_agent.llm.base import BaseLLM


class ClaudeLLM(BaseLLM):

    def __init__(self, api_key: str = "", model: str = "claude-sonnet-4-20250514"):
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key or None)

    def generate(self, prompt: str, system: str = "") -> str:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": 8192,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    def generate_json(self, prompt: str, system: str = "") -> dict:
        full_prompt = prompt + "\n\nRespond with valid JSON only, no markdown fences."
        text = self.generate(full_prompt, system)
        return self._extract_json(text)

    def supports_vision(self) -> bool:
        return True

    def generate_vision(self, prompt: str, image_paths: list[str],
                        system: str = "") -> str:
        import base64
        from pathlib import Path

        content: list[dict] = []
        for p in image_paths:
            suffix = Path(p).suffix.lower()
            media = "image/png" if suffix == ".png" else "image/jpeg"
            data = base64.standard_b64encode(Path(p).read_bytes()).decode()
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": media, "data": data},
            })
        content.append({"type": "text", "text": prompt})

        kwargs: dict = {
            "model": self.model,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": content}],
        }
        if system:
            kwargs["system"] = system
        response = self.client.messages.create(**kwargs)
        return response.content[0].text
