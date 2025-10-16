"""OpenAI adapter - minimal wrapper compatible with both openai<1 and openai>=1.

This adapter detects whether the installed `openai` package exposes the
modern `OpenAI` client (v1+). If available it uses the new client
(client.chat.completions.create / client.embeddings.create). Otherwise it
falls back to the legacy `openai.ChatCompletion.create` and
`openai.Embedding.create` calls.

The adapter keeps a synchronous style for simplicity (calls are blocking)
but exposes async methods so the rest of the codebase can await them.
"""
from __future__ import annotations

from typing import Any, Dict, List
import os

try:
    import openai
except Exception:
    openai = None


class OpenAIAdapter:
    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini"):
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OpenAI API key not provided")
        if openai is None:
            raise RuntimeError("openai package is required: pip install openai")

        # Support both the new OpenAI client (v1+) and the legacy API
        self.model = model
        if hasattr(openai, "OpenAI"):
            # new style: client = OpenAI(api_key=...)
            try:
                self.client = openai.OpenAI(api_key=key)
            except Exception:
                # fallback to setting env key and creating default client
                os.environ.setdefault("OPENAI_API_KEY", key)
                self.client = openai.OpenAI()
            self._use_new = True
        else:
            # legacy openai package
            openai.api_key = key
            self.client = openai
            self._use_new = False

    async def send(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Send a chat prompt and return the raw provider response.

        The return value shape differs between client versions; the caller
        should handle both shapes. This method is intentionally blocking
        (calls the sync client) but is async to fit the calling code.
        """
        # Use the modern OpenAI client if available
        if self._use_new:
            # client.chat.completions.create(...)
            resp = self.client.chat.completions.create(model=self.model, messages=[{"role": "user", "content": prompt}], **kwargs)
            return resp
        else:
            # legacy
            resp = self.client.ChatCompletion.create(model=self.model, messages=[{"role": "user", "content": prompt}], **kwargs)
            return resp

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if self._use_new:
            resp = self.client.embeddings.create(model="text-embedding-3-small", input=texts)
            # resp.data may be a list-like of objects or dicts
            data = getattr(resp, "data", None) or resp.get("data")
            return [d.get("embedding") if isinstance(d, dict) else getattr(d, "embedding") for d in data]
        else:
            resp = self.client.Embedding.create(model="text-embedding-3-small", input=texts)
            return [d['embedding'] for d in resp['data']]
