"""Abstract base class for LLM providers."""

from __future__ import annotations

import json
import re
import time
from abc import ABC, abstractmethod


class LLMResponseError(RuntimeError):
    """The provider returned an empty or unparseable response after retries."""


_JSON_INSTRUCTION = "\n\nRespond with valid JSON only, no markdown fences."
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class BaseLLM(ABC):

    #: retries after the first attempt; backoff doubles each retry
    max_retries = 2
    retry_backoff = 2.0

    @abstractmethod
    def generate(self, prompt: str, system: str = "") -> str:
        """Generate text completion."""

    def generate_json(self, prompt: str, system: str = "") -> dict:
        """Generate and parse a JSON response, retrying transient failures."""
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                text = self._generate_for_json(prompt + _JSON_INSTRUCTION, system)
                return self._extract_json(text)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff * (2**attempt))
        raise LLMResponseError(
            f"{type(self).__name__} failed after {self.max_retries + 1} attempts: {last_error}"
        ) from last_error

    def _generate_for_json(self, prompt: str, system: str) -> str:
        """Hook for providers with a native JSON mode (e.g. response_format)."""
        return self.generate(prompt, system)

    def supports_vision(self) -> bool:
        return False

    def generate_vision(self, prompt: str, image_paths: list[str],
                        system: str = "") -> str:
        """Generate a response from a prompt plus images (vision models only)."""
        raise NotImplementedError(f"{type(self).__name__} does not support vision input")

    def _extract_json(self, text: str | None) -> dict:
        if not text or not text.strip():
            raise LLMResponseError("empty LLM response")
        text = text.strip()

        candidates = []
        fence = _FENCE_RE.search(text)
        if fence:
            candidates.append(fence.group(1).strip())
        candidates.append(text)
        # last resort: the outermost {...} span, tolerating surrounding prose
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            candidates.append(text[start : end + 1])

        for candidate in candidates:
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                return data
        raise LLMResponseError(f"no valid JSON object in LLM response: {text[:200]!r}")
