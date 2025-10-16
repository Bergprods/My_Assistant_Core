"""Lightweight Home Assistant service placed under my_ai_assistant.services.

Accepts payloads and simulates device control actions.
"""
from __future__ import annotations

from typing import Any, Dict
import asyncio


class HomeAssistantService:
    async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        original = payload.get("Original", "")
        desc = payload.get("service_description", "")
        # Simulate executing a device command
        await asyncio.sleep(0.2)
        return {"ok": True, "action": "homeassistant_command", "original": original, "description": desc}
