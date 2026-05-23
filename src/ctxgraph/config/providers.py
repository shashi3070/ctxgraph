from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Optional

from ctxgraph.config.settings import Settings


def chat_completion(
    settings: Settings,
    system_prompt: str,
    user_prompt: str,
) -> Optional[str]:
    provider = settings.provider

    if provider == "ollama":
        return _ollama_chat(settings, system_prompt, user_prompt)
    elif provider == "claude":
        return _claude_chat(settings, system_prompt, user_prompt)
    elif provider == "openai":
        return _openai_chat(settings, system_prompt, user_prompt)
    else:
        return _custom_chat(settings, system_prompt, user_prompt)


def generate_summary(
    settings: Settings,
    code: str,
    context: str = "",
) -> Optional[str]:
    system = "You are a code analysis assistant. Summarize the following code concisely in 1-2 sentences."
    user = f"Context: {context}\n\nCode:\n```python\n{code[:2000]}\n```"

    return chat_completion(settings, system, user)


def _ollama_chat(settings: Settings, system: str, user: str) -> Optional[str]:
    url = settings.get_chat_url()
    payload = {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "temperature": settings.temperature,
    }

    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            return result.get("message", {}).get("content", "")
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None


def _claude_chat(settings: Settings, system: str, user: str) -> Optional[str]:
    api_key = settings.api_key
    if not api_key:
        return None

    url = settings.get_chat_url()
    payload = {
        "model": settings.model,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "max_tokens": settings.max_tokens,
        "temperature": settings.temperature,
    }

    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            return result.get("content", [{}])[0].get("text", "")
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None


def _openai_chat(settings: Settings, system: str, user: str) -> Optional[str]:
    api_key = settings.api_key
    if not api_key:
        return None

    url = settings.get_chat_url()
    payload = {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": settings.max_tokens,
        "temperature": settings.temperature,
    }

    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            return result.get("choices", [{}])[0].get("message", {}).get("content", "")
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None


def _custom_chat(settings: Settings, system: str, user: str) -> Optional[str]:
    url = settings.get_chat_url()
    payload = {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": settings.temperature,
    }

    headers = {"Content-Type": "application/json"}
    if settings.api_key:
        headers["Authorization"] = f"Bearer {settings.api_key}"

    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            return json.dumps(result)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None
