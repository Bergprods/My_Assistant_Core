"""Small CLI to demonstrate orchestrator routing using the new services.

This CLI creates an OrchestratorService with simple local stub agents so you can
exercise dispatch locally without external dependencies.
"""
import asyncio
from my_ai_assistant.services.agent_service import AgentService
from my_ai_assistant.services.orchestrator_service import OrchestratorService


class StubAgent:
    def __init__(self, name: str):
        self.name = name

    async def handle(self, payload):
        await asyncio.sleep(0.1)
        return {"ok": True, "agent": self.name, "payload": payload}


async def main():
    # Create a dummy AgentService that won't call LLMs for the CLI demo
    agent_service = AgentService(None)
    orch_svc = OrchestratorService(agent_service)

    orch_svc.register('github', StubAgent('github'), description='Handles repo and project tasks')
    orch_svc.register('homeassistant', StubAgent('homeassistant'), description='Controls home devices')
    orch_svc.register('smalltalk', StubAgent('smalltalk'), description='Casual conversation and small replies')

    print('Services:')
    for k, v in orch_svc.list_services().items():
        print('-', k, ':', v)

    original = 'Skapa projektet Test och sätt på lamporna i vardagsrummet'
    print('\nDispatching original:', original)
    resp = await orch_svc.dispatch(original, wait_for=2.0)
    print('\nDispatch result:', resp)


if __name__ == '__main__':
    asyncio.run(main())
