# ai_providers.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
import os
import json
import logging
import httpx

from openai import AsyncOpenAI
from openai import APIError, RateLimitError  # for OpenAI errors

logger = logging.getLogger(__name__)

Message = Dict[str, str]

class ChatResult:
    def __init__(self, text: str, tokens_used: Optional[int], model: str, provider: str):
        self.text = text
        self.tokens_used = tokens_used
        self.model = model
        self.provider = provider

class BaseProvider:
    name: str
    async def chat(self, *, messages: List[Message], model: str, max_tokens: int, temperature: float) -> ChatResult:
        raise NotImplementedError

# -------------------------
# OpenAI provider (SDK)
# -------------------------
class OpenAIProvider(BaseProvider):
    name = "openai"

    def __init__(self, api_key: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    async def chat(self, *, messages: List[Message], model: str, max_tokens: int, temperature: float) -> ChatResult:
        resp = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        text = resp.choices[0].message.content or ""
        tokens = resp.usage.total_tokens if resp.usage else None
        return ChatResult(text=text, tokens_used=tokens, model=model, provider=self.name)

# -------------------------
# Grok/xAI provider (raw HTTP)
# -------------------------
class GrokProvider(BaseProvider):
    """
    Separate implementation using httpx directly.
    API: https://api.x.ai/v1 (OpenAI-compatible)
    """
    name = "grok"

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.x.ai/v1"):
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    async def chat(self, *, messages: List[Message], model: str, max_tokens: int, temperature: float) -> ChatResult:
        # POST /chat/completions (OpenAI-compatible shape)
        payload = {
            "model": model,                     # e.g., "grok-4" (set in settings)
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        r = await self._client.post("/chat/completions", json=payload)
        # xAI uses OpenAI-like error body; raise for non-2xx so calling code can fallback
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            # Repackage a few common cases
            if r.status_code == 429:
                raise RateLimitError(message="xAI: rate/quota exceeded")  # reuse OpenAI rate error type for uniform handling
            # Let caller decide for other codes
            raise

        data = r.json()
        # Expected shape: { choices: [ { message: { content: "..." } } ], usage: { total_tokens: ... } }
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except Exception:
            text = ""

        tokens = None
        try:
            tokens = data.get("usage", {}).get("total_tokens")
        except Exception:
            pass

        return ChatResult(text=text, tokens_used=tokens, model=model, provider=self.name)

    async def aclose(self):
        await self._client.aclose()
