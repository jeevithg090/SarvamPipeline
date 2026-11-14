"""Streaming client for Sarvam's OpenAI-compatible chat completions API.

`stream_llm` yields reply text deltas and transparently runs the
function-calling loop: when the model asks for tools, they are executed and
their results fed back before streaming continues.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from agent_functions import FUNCTION_DEFINITIONS, call_function

logger = logging.getLogger(__name__)

SARVAM_CHAT_URL = "https://api.sarvam.ai/v1/chat/completions"
OPENAI_TOOLS = [{"type": "function", "function": f} for f in FUNCTION_DEFINITIONS]
MAX_TOOL_ROUNDS = 5


class LLMError(RuntimeError):
    """The chat completions API returned an error response."""


def parse_sse_line(line: str) -> dict[str, Any] | None:
    """Decode one server-sent-events line into a JSON chunk.

    Returns None for keep-alives, comments, `[DONE]` and malformed payloads.
    """
    if not line.startswith("data:"):
        return None
    payload = line[5:].strip()
    if not payload or payload == "[DONE]":
        return None
    try:
        chunk = json.loads(payload)
    except json.JSONDecodeError:
        logger.warning("Skipping malformed SSE payload: %.200s", payload)
        return None
    return chunk if isinstance(chunk, dict) else None


class ToolCallAccumulator:
    """Reassembles tool calls that arrive split across streamed deltas."""

    def __init__(self) -> None:
        self._slots: dict[int, dict[str, str]] = {}

    def __bool__(self) -> bool:
        return bool(self._slots)

    def add(self, deltas: list[dict[str, Any]]) -> None:
        for tc in deltas:
            slot = self._slots.setdefault(
                tc.get("index", 0), {"id": "", "name": "", "arguments": ""}
            )
            if tc.get("id"):
                slot["id"] = tc["id"]
            fn = tc.get("function") or {}
            if fn.get("name"):
                slot["name"] += fn["name"]
            if fn.get("arguments"):
                slot["arguments"] += fn["arguments"]

    def calls(self) -> list[dict[str, str]]:
        return [self._slots[i] for i in sorted(self._slots)]


def parse_arguments(raw: str) -> dict[str, Any]:
    """Parse a tool call's JSON arguments, tolerating empty or invalid input."""
    try:
        args = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return args if isinstance(args, dict) else {}


async def stream_llm(
    messages: list[dict[str, Any]],
    model: str,
    api_key: str,
    *,
    client: httpx.AsyncClient | None = None,
    max_tokens: int = 200,
) -> AsyncIterator[str]:
    """Yield reply text deltas from Sarvam chat; handles the function loop.

    `messages` is extended in place with assistant tool-call and tool-result
    messages so the caller's history stays consistent.
    """
    own_client = client is None
    http = client or httpx.AsyncClient(timeout=60)
    try:
        for _ in range(MAX_TOOL_ROUNDS):
            tool_calls = ToolCallAccumulator()
            async with http.stream(
                "POST",
                SARVAM_CHAT_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": messages,
                    "tools": OPENAI_TOOLS,
                    "reasoning_effort": None,  # thinking off: latency-critical
                    "max_tokens": max_tokens,
                    "stream": True,
                },
            ) as resp:
                if resp.status_code != 200:
                    body = (await resp.aread()).decode(errors="replace")
                    logger.error("LLM request failed (%s): %.500s", resp.status_code, body)
                    raise LLMError(f"LLM request failed with HTTP {resp.status_code}")
                async for line in resp.aiter_lines():
                    chunk = parse_sse_line(line)
                    if not chunk or not chunk.get("choices"):
                        continue
                    delta = chunk["choices"][0].get("delta") or {}
                    if delta.get("content"):
                        yield delta["content"]
                    tool_calls.add(delta.get("tool_calls") or [])

            if not tool_calls:
                return

            calls = tool_calls.calls()
            messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": c["id"],
                            "type": "function",
                            "function": {"name": c["name"], "arguments": c["arguments"]},
                        }
                        for c in calls
                    ],
                }
            )
            for c in calls:
                result = await call_function(c["name"], parse_arguments(c["arguments"]))
                messages.append(
                    {"role": "tool", "tool_call_id": c["id"], "content": json.dumps(result)}
                )
        logger.warning("Stopped after %d tool-call rounds without a text reply", MAX_TOOL_ROUNDS)
    finally:
        if own_client:
            await http.aclose()
