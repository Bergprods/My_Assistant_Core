from __future__ import annotations

from typing import Any
import json
import re
import logging

logger = logging.getLogger(__name__)


def parse_json_from_text(text: str) -> Any:
    """Tolerant JSON extraction from model text responses.

    Strips common wrappers (code fences, single backticks) and attempts
    to parse a top-level JSON object or a JSON substring.
    """
    if not text:
        return None
    s = text.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.I)
    s = re.sub(r"\s*```$", "", s, flags=re.I)
    if s.startswith('`') and s.endswith('`'):
        s = s[1:-1].strip()

    try:
        return json.loads(s)
    except Exception:
        pass

    m = re.search(r"(\{.*\})", s, flags=re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            return None
    return None


def validate_parsed_with_schema(parsed: Any) -> bool:
    try:
        import jsonschema
        import pathlib
        schema_path = pathlib.Path(__file__).resolve().parents[2] / 'prompts' / 'json-templates' / 'orchestrator.json'
        with open(schema_path, 'r', encoding='utf8') as f:
            schema = json.load(f)
        jsonschema.validate(instance=parsed, schema=schema)
        return True
    except Exception as e:
        try:
            logger.warning('Schema validation error: %s', e)
        except Exception:
            pass
        return False
