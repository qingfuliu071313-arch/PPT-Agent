"""Configuration management."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    provider: str = "claude"
    claude_model: str = "claude-sonnet-4-20250514"
    claude_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_api_key: str = ""

    def __post_init__(self):
        if not self.claude_api_key:
            self.claude_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.gemini_api_key:
            self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        if not self.deepseek_api_key:
            self.deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY", "")


@dataclass
class PipelineConfig:
    outline_provider: str = ""
    content_provider: str = ""
    max_slides: int = 30
    output_dir: str = "./output"

    def __post_init__(self):
        if not self.outline_provider:
            self.outline_provider = "default"
        if not self.content_provider:
            self.content_provider = "default"


@dataclass
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)

    @classmethod
    def from_env(cls) -> AppConfig:
        provider = os.environ.get("PPT_AGENT_PROVIDER", "claude")
        return cls(
            llm=LLMConfig(provider=provider),
            pipeline=PipelineConfig(
                output_dir=os.environ.get("PPT_AGENT_OUTPUT", "./output"),
            ),
        )
