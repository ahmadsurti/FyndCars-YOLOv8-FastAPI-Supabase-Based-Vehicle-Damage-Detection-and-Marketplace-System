from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Protocol
import httpx


class LLMProvider(Protocol):
    def generate(self, prompt: str) -> str: ...


@dataclass
class OpenAICompatibleProvider:
    """
    Minimal OpenAI-compatible chat client.
    Supports OpenAI, DeepSeek, Groq, OpenRouter — any /chat/completions endpoint.
    Env: LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
    """
    base_url: str
    api_key: str
    model: str = "gpt-4o-mini"
    timeout_s: float = 30.0

    def generate(self, prompt: str) -> str:
        # Normalise: strip trailing slash and any existing /v1 suffix to avoid /v1/v1
        base = self.base_url.rstrip("/")
        if not base.endswith("/v1"):
            base = base + "/v1"
        url = base + "/chat/completions"

        r = httpx.post(
            url,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": "You are a senior vehicle damage assessor. Be concise and practical."},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=self.timeout_s,
        )
        r.raise_for_status()
        try:
            return (r.json()["choices"][0]["message"]["content"] or "").strip()
        except Exception:
            return ""


@dataclass
class NoopProvider:
    """Fallback when no LLM configured."""
    def generate(self, prompt: str) -> str:
        return ""


def build_provider_from_env() -> LLMProvider:
    base_url = os.getenv("LLM_BASE_URL", "").strip()
    api_key = os.getenv("LLM_API_KEY", "").strip()
    model = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()
    if base_url and api_key:
        return OpenAICompatibleProvider(base_url=base_url, api_key=api_key, model=model)
    return NoopProvider()
