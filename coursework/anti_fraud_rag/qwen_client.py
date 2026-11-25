from __future__ import annotations

from openai import OpenAI

from .config import AppConfig


class QwenClient:
    def __init__(self, config: AppConfig, api_key: str | None = None) -> None:
        key = api_key or config.qwen_api_key
        if not key:
            raise RuntimeError("DASHSCOPE_API_KEY is not configured.")
        self.model = config.qwen_model
        self.client = OpenAI(
            api_key=key,
            base_url=config.qwen_base_url,
            timeout=config.qwen_timeout_seconds,
        )

    def complete(self, messages: list[dict[str, str]], temperature: float = 0.1) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
