import asyncio
import pytest

from my_ai_assistant.assistant import BaseAssistant

class DummyAdapter:
    async def send(self, prompt: str, **kwargs):
        return {"reply": f"echo: {prompt}"}
    async def embed(self, texts):
        return [[0.1]*8 for _ in texts]

@pytest.mark.asyncio
async def test_generate():
    adapter = DummyAdapter()
    assistant = BaseAssistant(adapter)
    res = await assistant.generate("hello")
    assert res["ok"]
    assert res["resp"]["reply"] == "echo: hello"
