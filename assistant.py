"""Base assistant implementation and interface."""
from __future__ import annotations

from typing import Any, Dict, Optional, Protocol
import logging

logger = logging.getLogger(__name__)


class ProviderAdapter(Protocol):
    async def send(self, prompt: str, **kwargs) -> Dict[str, Any]:
        ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class BaseAssistant:
    def __init__(self, adapter: ProviderAdapter, *, default_params: Optional[Dict[str, Any]] = None):
        self.adapter = adapter
        self.default_params = default_params or {}

    async def generate(self, prompt: str, **params) -> Dict[str, Any]:
        payload = {**self.default_params, **params}
        try:
            resp = await self.adapter.send(prompt, **payload)
            return {"ok": True, "resp": resp}
        except Exception as e:
            logger.exception("Assistant generate failed")
            return {"ok": False, "error": str(e)}

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await self.adapter.embed(texts)
