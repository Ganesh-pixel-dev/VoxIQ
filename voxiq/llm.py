"""Thin client for a local Ollama server. Nothing leaves the machine."""
import json

import requests

from . import config


class LLMUnavailable(RuntimeError):
    pass


def available() -> dict:
    """Is Ollama up, and is the configured model pulled?"""
    try:
        r = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=3)
        r.raise_for_status()
        names = [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return {"up": False, "model": config.LLM_MODEL, "model_ready": False}
    ready = config.LLM_MODEL in names or f"{config.LLM_MODEL}:latest" in names
    return {"up": True, "model": config.LLM_MODEL, "model_ready": ready}


def chat(system: str, user: str, json_mode: bool = False, temperature: float = 0.4) -> str:
    body = {
        "model": config.LLM_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
        "options": {"temperature": temperature},
    }
    if json_mode:
        body["format"] = "json"
    try:
        r = requests.post(f"{config.OLLAMA_URL}/api/chat", json=body, timeout=config.LLM_TIMEOUT)
    except requests.RequestException as e:
        raise LLMUnavailable(f"Ollama is not reachable at {config.OLLAMA_URL}. Start it with `ollama serve`.") from e
    if r.status_code == 404:
        raise LLMUnavailable(f"Model '{config.LLM_MODEL}' is not pulled. Run `ollama pull {config.LLM_MODEL}`.")
    if not r.ok:
        raise LLMUnavailable(f"Ollama returned {r.status_code}.")
    return r.json()["message"]["content"].strip()


def chat_json(system: str, user: str) -> dict:
    text = chat(system, user, json_mode=True)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise LLMUnavailable("The model returned something that was not valid JSON.") from e
