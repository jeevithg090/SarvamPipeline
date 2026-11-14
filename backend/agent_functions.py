"""Function calling for the voice agent.

Three layers: definitions (sent to the LLM) -> FUNCTION_MAP (routing) ->
implementations. The implementations below are demo stubs; replace them
with real services.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

AgentFunction = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]

# --- Implementations (mock business logic; replace with real services) ---


async def get_current_time(arguments: dict[str, Any]) -> dict[str, Any]:
    return {"current_time": datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")}


async def get_weather(arguments: dict[str, Any]) -> dict[str, Any]:
    city = str(arguments.get("city") or "unknown")
    return {"city": city, "forecast": "sunny", "temperature_c": 31}


# --- Definitions sent to the LLM as OpenAI-style tools ---

FUNCTION_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "get_current_time",
        "description": "Get the current local date and time.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_weather",
        "description": "Get the current weather forecast for a city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name, e.g. 'Hyderabad'"}
            },
            "required": ["city"],
        },
    },
]

FUNCTION_MAP: dict[str, AgentFunction] = {
    "get_current_time": get_current_time,
    "get_weather": get_weather,
}


async def call_function(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Run a tool by name, converting failures into an error payload for the LLM."""
    func = FUNCTION_MAP.get(name)
    if func is None:
        return {"error": f"unknown function: {name}"}
    try:
        return await func(arguments)
    except Exception as exc:  # errors are reported back to the model
        logger.exception("Function %s failed", name)
        return {"error": str(exc)}
