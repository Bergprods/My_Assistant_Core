"""Lightweight GitHub service placed under my_ai_assistant.services.

This mirrors the former agents/github_service.py but is a minimal
service implementation suitable for registering with OrchestratorService.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
import asyncio


class GitHubService:
    def __init__(self, issue_service: Optional[Any] = None, project_service: Optional[Any] = None):
        self.issue_service = issue_service
        self.project_service = project_service

    async def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        original = payload.get("Original", "")
        desc = payload.get("service_description", "")

        if not original:
            return {"ok": False, "error": "missing original text"}

        # Simulate creating an issue or scheduling background work
        if self.issue_service:
            try:
                loop = asyncio.get_running_loop()
                res = await loop.run_in_executor(None, self.issue_service.create_issue, original, desc, None)
                return {"ok": True, "action": "create_issue", "result": res}
            except Exception as e:
                return {"ok": False, "error": f"issue_service_failed: {e}"}

        asyncio.create_task(self._simulate_create_issue(original, desc))
        return {"ok": True, "status": "accepted", "note": "scheduled simulated work without backend"}

    async def _simulate_create_issue(self, original: str, desc: str) -> Dict[str, Any]:
        await asyncio.sleep(0.5)
        return {"ok": True, "message": "simulated issue created", "original": original, "description": desc}
