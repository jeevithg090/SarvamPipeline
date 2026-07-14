"""Function calling for the voice agent.

Three layers, following deepgram-devs/flask-agent-function-calling-demo:
definitions (sent to the LLM) -> FUNCTION_MAP (routing) -> implementations.
"""

from datetime import datetime

# --- Implementations (mock business logic; replace with real services) ---


async def get_current_time(arguments: dict) -> dict:
    return {"current_time": datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")}


async def get_weather(arguments: dict) -> dict:
    city = arguments.get("city", "unknown")
    return {"city": city, "forecast": "sunny", "temperature_c": 31}


# --- Definitions sent to the LLM in Settings ---

FUNCTION_DEFINITIONS = [
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

FUNCTION_MAP = {
    "get_current_time": get_current_time,
    "get_weather": get_weather,
}
