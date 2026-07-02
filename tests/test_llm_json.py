"""Tests for BaseLLM JSON extraction and retry behavior."""

from __future__ import annotations

import pytest

from ppt_agent.llm.base import BaseLLM, LLMResponseError


class FakeLLM(BaseLLM):
    retry_backoff = 0.0  # no sleeping in tests

    def __init__(self, responses: list):
        self._responses = list(responses)
        self.calls = 0

    def generate(self, prompt: str, system: str = "") -> str:
        self.calls += 1
        r = self._responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


# ── _extract_json ────────────────────────────────────────────

EXTRACT_CASES = [
    ('{"a": 1}', {"a": 1}),
    ('  {"a": 1}  ', {"a": 1}),
    ('```json\n{"a": 1}\n```', {"a": 1}),
    ('```\n{"a": 1}\n```', {"a": 1}),
    ('Here is the JSON:\n{"a": 1}', {"a": 1}),
    ('{"a": 1}\nHope this helps!', {"a": 1}),
    ('Sure!\n```json\n{"a": {"b": [1, 2]}}\n```\nLet me know.', {"a": {"b": [1, 2]}}),
    # unclosed fence — brace fallback must still find it
    ('```json\n{"a": 1}', {"a": 1}),
    # nested braces in prose around the object
    ('prefix {"a": {"b": 2}} suffix', {"a": {"b": 2}}),
]


@pytest.mark.parametrize("text,expected", EXTRACT_CASES)
def test_extract_json_variants(text, expected):
    assert FakeLLM([])._extract_json(text) == expected


@pytest.mark.parametrize("text", [None, "", "   ", "no json here", "[1, 2, 3]"])
def test_extract_json_rejects_non_objects(text):
    with pytest.raises(LLMResponseError):
        FakeLLM([])._extract_json(text)


# ── generate_json retry loop ─────────────────────────────────

def test_generate_json_first_try():
    llm = FakeLLM(['{"ok": true}'])
    assert llm.generate_json("p") == {"ok": True}
    assert llm.calls == 1


def test_generate_json_retries_bad_json_then_succeeds():
    llm = FakeLLM(["garbage", "still garbage", '{"ok": 1}'])
    assert llm.generate_json("p") == {"ok": 1}
    assert llm.calls == 3


def test_generate_json_retries_transport_error():
    llm = FakeLLM([ConnectionError("boom"), '{"ok": 1}'])
    assert llm.generate_json("p") == {"ok": 1}
    assert llm.calls == 2


def test_generate_json_exhausts_retries():
    llm = FakeLLM(["bad", "bad", "bad"])
    with pytest.raises(LLMResponseError, match="after 3 attempts"):
        llm.generate_json("p")
    assert llm.calls == 3
