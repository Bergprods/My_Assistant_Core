"""Simple CLI to call BaseAssistant synchronously for quick testing."""
import asyncio
import os
import sys
from my_ai_assistant.assistant import BaseAssistant
from my_ai_assistant.providers.openai_adapter import OpenAIAdapter

async def main():
    prompt = "\n".join(sys.argv[1:]) or "Say hello"
    adapter = OpenAIAdapter()
    assistant = BaseAssistant(adapter)
    resp = await assistant.generate(prompt)
    print(resp)

if __name__ == '__main__':
    asyncio.run(main())
