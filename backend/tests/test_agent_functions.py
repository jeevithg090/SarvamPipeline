from agent_functions import FUNCTION_DEFINITIONS, FUNCTION_MAP, call_function


def test_every_definition_has_an_implementation():
    assert {d["name"] for d in FUNCTION_DEFINITIONS} == set(FUNCTION_MAP)


async def test_get_weather_echoes_city():
    result = await call_function("get_weather", {"city": "Hyderabad"})
    assert result["city"] == "Hyderabad"
    assert "temperature_c" in result


async def test_get_current_time_returns_string():
    result = await call_function("get_current_time", {})
    assert isinstance(result["current_time"], str)


async def test_unknown_function_returns_error():
    assert "error" in await call_function("does_not_exist", {})


async def test_function_exceptions_become_error_payload(monkeypatch):
    async def boom(_args):
        raise ValueError("bad input")

    monkeypatch.setitem(FUNCTION_MAP, "boom", boom)
    assert await call_function("boom", {}) == {"error": "bad input"}
