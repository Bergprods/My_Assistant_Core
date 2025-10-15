from __future__ import annotations

from typing import Any, Dict, List, Callable, Optional
import logging
import asyncio
import datetime

logger = logging.getLogger(__name__)


class OrchestratorService:
    """OrchestratorService performs two roles now:
    - Interpretation: use AgentService to ask the LLM what intents are relevant
    - Registry & dispatch: keep a registry of service agents and schedule tasks
    """

    def __init__(self, agent_service: Any):
        self.agent_service = agent_service
        # registry: name -> {agent, description}
        self._registry: Dict[str, Dict[str, Any]] = {}
        self._bg_tasks: List[asyncio.Task] = []
        self.on_task_done: Optional[Callable[[str, Dict[str, Any]], None]] = None

    # --- Interpretation helpers -------------------------------------------------
    def _build_prompt(self, original: str, services: Dict[str, str]) -> str:
        service_list = ", ".join([f"{k}: {v}" for k, v in services.items()]) or "(none)"
        prompt = (
            "You are an assistant that MUST respond with a JSON object ONLY (no prose, no markdown, no explanation).\n"
            "Return exactly one JSON object and nothing else. The JSON object must have these keys:\n"
            "  - intents: an array of service names (strings) that should handle the request, in priority order.\n"
            "  - directResponse: a short friendly reply to the user acknowledging the request.\n"
            "  - intentDescriptions: an object mapping each intent name to a one-line description of what should be done.\n"
            "Available services: "
            + service_list
            + "\n"
            + "User message: "
            + original
            + "\n"
            + (
                "IMPORTANT: do not include any text before or after the JSON object. Respond with the JSON object only.\n"
                "Include an optional metadata object with 'confidence' (0-1) and/or 'timestamp' (ISO 8601) if available."
            )
        )
        return prompt

    async def _send_and_extract(self, prompt: str) -> Optional[str]:
        """Send prompt via agent_service and return the extracted assistant text (tolerant)."""
        resp = await self.agent_service.send_prompt(prompt)
        text = None
        if isinstance(resp, dict) and resp.get("ok"):
            text = resp.get("resp")
        elif isinstance(resp, str):
            text = resp
        try:
            logger.info("OrchestratorService raw response: %s", text)
        except Exception:
            pass
        # use response_tools extraction if available
        try:
            from my_ai_assistant.utils.response_tools import extract_text_from_assistant_resp

            extracted = extract_text_from_assistant_resp(text)
            return extracted or text
        except Exception:
            return text

    def _parse_text(self, text: Any) -> Any:
        """Tolerant parse: strip fences and extract a single JSON object if present."""
        if not text:
            return None
        try:
            import json, re

            s = text.strip()
            s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.I)
            s = re.sub(r"\s*```$", "", s, flags=re.I)
            if s.startswith("`") and s.endswith("`"):
                s = s[1:-1].strip()
            try:
                return json.loads(s)
            except Exception:
                m = re.search(r"(\{.*\})", s, flags=re.S)
                if m:
                    return json.loads(m.group(1))
        except Exception:
            return None

    def _validate_parsed(self, parsed: Any) -> bool:
        try:
            import jsonschema, json, pathlib
            schema_path = (
                pathlib.Path(__file__).resolve().parents[2] / "prompts" / "json-templates" / "orchestrator.json"
            )
            with open(schema_path, "r", encoding="utf8") as f:
                schema = json.load(f)
            jsonschema.validate(instance=parsed, schema=schema)
            return True
        except Exception as e:
            logger.warning("OrchestratorService validation error: %s", e)
            return False

    async def _attempt_parse_with_retry(self, original: str, services: Dict[str, str]) -> Any:
        """Try interpret once, then retry with a clarifying prompt if validation fails."""
        prompt = self._build_prompt(original, services)
        text = await self._send_and_extract(prompt)
        parsed = self._parse_text(text)
        if self._validate_parsed(parsed):
            return parsed

        # retry
        retry_prompt = (
            prompt
            + "\n\nThe previous response was not valid JSON according to the required schema. Reply ONLY with a single JSON object that matches the schema exactly."
        )
        text2 = await self._send_and_extract(retry_prompt)
        parsed2 = self._parse_text(text2)
        if self._validate_parsed(parsed2):
            return parsed2
        logger.warning("OrchestratorService: invalid JSON after retry. First: %s Retry: %s", text, text2)
        raise RuntimeError("Assistant returned invalid JSON after retry")

    def _normalize_parsed(self, parsed: Any) -> Dict[str, Any]:
        """Normalize key names and ensure metadata includes an ISO8601 UTC timestamp."""
        from copy import deepcopy

        p = deepcopy(parsed) if parsed else {}
        result: Dict[str, Any] = {
            "intents": p.get("intents") or p.get("services") or [],
            "directResponse": p.get("directResponse") or p.get("direct_response") or p.get("reply") or "",
            "intentDescriptions": p.get("intentDescriptions") or p.get("intent_descriptions") or {},
        }
        metadata = p.get("metadata") or {}
        # ensure timestamp present
        ts = metadata.get("timestamp")
        if not ts:
            # ISO 8601 UTC
            metadata["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result["metadata"] = metadata
        return result

    async def interpret(self, original: str, services: Dict[str, str]) -> Dict[str, Any]:
        """High-level interpret API kept for backward compatibility."""
        parsed = await self._attempt_parse_with_retry(original, services)
        return self._normalize_parsed(parsed)

    # registry and dispatch
    def register(self, name: str, agent: Any, description: str = "") -> None:
        self._registry[name.lower()] = {"agent": agent, "description": description}

    def list_services(self) -> Dict[str, str]:
        return {name: info.get("description", "") for name, info in self._registry.items()}

    def get_registered(self) -> List[str]:
        return list(self._registry.keys())

    def _build_payload(self, service_name: str, original: str) -> Dict[str, Any]:
        info = self._registry.get(service_name, {})
        return {
            "Original": original,
            "service_name": service_name,
            "service_description": info.get("description", ""),
            "meta": {"source": "orchestrator_service", "service": service_name},
        }

    async def dispatch(self, original: str, services: Optional[List[str]] = None, wait_for: Optional[float] = None) -> Dict[str, Any]:
        if services:
            targets = [s.lower() for s in services]
        else:
            targets = self.get_registered()

        dispatched: Dict[str, Any] = {}
        interpreted = None
        # call interpret via agent_service
        try:
            interpreted = await self.interpret(original, self.list_services())
            if interpreted and isinstance(interpreted.get("intents"), list):
                targets = [s.lower() for s in interpreted.get("intents")]
        except Exception:
            interpreted = None

        tasks = []
        for t in targets:
            entry = self._registry.get(t)
            if not entry:
                dispatched[t] = {"ok": False, "error": "service-not-registered"}
                continue
            agent = entry["agent"]
            payload = self._build_payload(t, original)
            if interpreted and interpreted.get("intentDescriptions"):
                desc = interpreted.get("intentDescriptions").get(t)
                if desc:
                    payload["service_description"] = desc
            task = asyncio.create_task(self._run_agent_task(t, agent, payload))
            tasks.append((t, task))
            self._bg_tasks.append(task)
            dispatched[t] = {"ok": True, "status": "scheduled"}

        results: Dict[str, Any] = {}
        if wait_for and tasks:
            done, pending = await asyncio.wait([t for _, t in tasks], timeout=wait_for)
            for name, task in tasks:
                if task in done:
                    try:
                        results[name] = task.result()
                    except Exception as e:
                        results[name] = {"ok": False, "error": str(e)}
                else:
                    results[name] = {"ok": False, "status": "pending"}

        return {"services_available": self.list_services(), "targets": targets, "dispatched": dispatched, "results": results}

    async def _run_agent_task(self, name: str, agent: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            res = await agent.handle(payload)
            if self.on_task_done:
                try:
                    self.on_task_done(name, res)
                except Exception:
                    pass
            return res
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _try_parse_text(self, text: Any) -> Any:
        # handle SDK/dict shapes and BaseAssistant wrapper
        try:
            from my_ai_assistant.utils.response_tools import extract_text_from_assistant_resp
        except Exception:
            extract_text_from_assistant_resp = None

        if extract_text_from_assistant_resp:
            text = extract_text_from_assistant_resp(text)

        if not text:
            return None
        try:
            import json, re
            s = text.strip()
            s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.I)
            s = re.sub(r"\s*```$", "", s, flags=re.I)
            if s.startswith('`') and s.endswith('`'):
                s = s[1:-1].strip()
            try:
                return json.loads(s)
            except Exception:
                m = re.search(r"(\{.*\})", s, flags=re.S)
                if m:
                    return json.loads(m.group(1))
        except Exception:
            return None

    def _validate_parsed(self, parsed: Any) -> bool:
        try:
            import jsonschema, json, pathlib
            schema_path = pathlib.Path(__file__).resolve().parents[2] / 'prompts' / 'json-templates' / 'orchestrator.json'
            with open(schema_path, 'r', encoding='utf8') as f:
                schema = json.load(f)
            jsonschema.validate(instance=parsed, schema=schema)
            return True
        except Exception as e:
            logger.warning('OrchestratorService validation error: %s', e)
            return False
