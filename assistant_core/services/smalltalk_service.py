"""SmallTalk service placed under my_ai_assistant.services.

Simple echo-like handler for confirmations and casual replies.
"""
from __future__ import annotations

from typing import Any, Dict
import asyncio


class SmallTalkService:
    async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        original = payload.get("Original", "")
        await asyncio.sleep(0.05)
        return {"ok": True, "action": "smalltalk", "reply": f"Ack: {original}"}
