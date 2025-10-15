from __future__ import annotations

from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)


class AgentService:
    """Service responsible for direct communication with the LLM via a provided assistant.

    The assistant should implement async generate(prompt, **params) -> {ok: bool, resp: ...}
    """

    def __init__(self, assistant: Any):
        self.assistant = assistant

    async def send_prompt(self, prompt: str, **kwargs) -> Any:
        """Send a prompt to the assistant and return the raw assistant response."""
        return await self.assistant.generate(prompt, **kwargs)

