"""Abstract base class for LLM providers."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod


class BaseLLM(ABC):

    @abstractmethod
    def generate(self, prompt: str, system: str = "") -> str:
        """Generate text completion."""

    @abstractmethod
    def generate_json(self, prompt: str, system: str = "") -> dict:
        """Generate and parse a JSON response."""

    def supports_vision(self) -> bool:
        return False

    def generate_vision(self, prompt: str, image_paths: list[str],
                        system: str = "") -> str:
        """Generate a response from a prompt plus images (vision models only)."""
        raise NotImplementedError(f"{type(self).__name__} does not support vision input")

    def _extract_json(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:]  # remove ```json
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        return json.loads(text)
