from __future__ import annotations

from typing import Any, Optional


def extract_text_from_assistant_resp(resp: Any) -> Optional[str]:
    """Extract text content from various assistant response shapes.

    Accepts:
    - the BaseAssistant wrapper return: {'ok': True, 'resp': <inner>}
    - SDK ChatCompletion objects or dict responses
    - plain string responses
    """
    if resp is None:
        return None

    # If BaseAssistant wrapper
    if isinstance(resp, dict) and resp.get("ok"):
        inner = resp.get("resp")
    else:
        inner = resp

    # If inner is already a string
    if isinstance(inner, str):
        return inner

    # If dict-like
    if isinstance(inner, dict):
        choices = inner.get("choices")
    else:
        # may be SDK object with attribute .choices
        choices = getattr(inner, "choices", None)

    if choices and isinstance(choices, (list, tuple)):
        first = choices[0]
        # attribute-style
        msg = getattr(first, "message", None) or getattr(first, "delta", None)
        if msg is not None:
            content = getattr(msg, "content", None) if not isinstance(msg, dict) else msg.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, dict):
                text = content.get("text")
                if text:
                    return text
        # dict-style fallback
        if isinstance(first, dict):
            msg = first.get("message") or first.get("delta")
            if isinstance(msg, dict):
                content = msg.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, dict):
                    text = content.get("text")
                    if text:
                        return text
            text = first.get("text")
            if text:
                return text

    # last resort: try string conversion
    try:
        return str(inner)
    except Exception:
        return None
