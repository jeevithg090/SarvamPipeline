import json

import httpx
import pytest

from llm import (
    LLMError,
    ToolCallAccumulator,
    parse_arguments,
    parse_sse_line,
    stream_llm,
)


def sse(*chunks):
    lines = [f"data: {json.dumps(c)}" for c in chunks] + ["data: [DONE]"]
    return "\n\n".join(lines) + "\n\n"


def text_chunk(text):
    return {"choices": [{"delta": {"content": text}}]}


def test_parse_sse_line():
    assert parse_sse_line('data: {"a": 1}') == {"a": 1}
    assert parse_sse_line('data:{"a": 1}') == {"a": 1}
    assert parse_sse_line("data: [DONE]") is None
    assert parse_sse_line(": keep-alive") is None
    assert parse_sse_line("") is None
    assert parse_sse_line("data: {not json") is None
    assert parse_sse_line("data: [1, 2]") is None


def test_tool_call_accumulator_merges_fragments():
    acc = ToolCallAccumulator()
    assert not acc
    acc.add([{"index": 0, "id": "call_1", "function": {"name": "get_", "arguments": '{"ci'}}])
    acc.add([{"index": 0, "function": {"name": "weather", "arguments": 'ty": "Pune"}'}}])
    acc.add([{"index": 1, "id": "call_2", "function": {"name": "get_current_time"}}])
    assert acc
    assert acc.calls() == [
        {"id": "call_1", "name": "get_weather", "arguments": '{"city": "Pune"}'},
        {"id": "call_2", "name": "get_current_time", "arguments": ""},
    ]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("", {}), ('{"x": 1}', {"x": 1}), ("[1]", {}), ("{oops", {})],
)
def test_parse_arguments(raw, expected):
    assert parse_arguments(raw) == expected


async def collect(gen):
    return [part async for part in gen]


async def test_streams_text_deltas():
    def handler(request):
        body = json.loads(request.content)
        assert body["model"] == "sarvam-30b"
        assert body["stream"] is True
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(200, text=sse(text_chunk("Hel"), {"choices": []}, text_chunk("lo")))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        parts = await collect(
            stream_llm([{"role": "user", "content": "hi"}], "sarvam-30b", "test-key", client=client)
        )
    assert parts == ["Hel", "lo"]


async def test_runs_tool_calls_then_streams_answer():
    requests = []

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        if len(requests) == 1:
            return httpx.Response(
                200,
                text=sse(
                    {
                        "choices": [
                            {
                                "delta": {
                                    "tool_calls": [
                                        {
                                            "index": 0,
                                            "id": "call_1",
                                            "function": {
                                                "name": "get_weather",
                                                "arguments": '{"city": "Delhi"}',
                                            },
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ),
            )
        return httpx.Response(200, text=sse(text_chunk("It is sunny in Delhi.")))

    messages = [{"role": "user", "content": "weather in Delhi?"}]
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        parts = await collect(stream_llm(messages, "sarvam-30b", "k", client=client))

    assert parts == ["It is sunny in Delhi."]
    assert len(requests) == 2
    roles = [m["role"] for m in requests[1]["messages"]]
    assert roles == ["user", "assistant", "tool"]
    tool_result = json.loads(requests[1]["messages"][2]["content"])
    assert tool_result["city"] == "Delhi"


async def test_http_error_raises_llm_error():
    def handler(request):
        return httpx.Response(401, json={"error": "invalid key"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(LLMError, match="401"):
            await collect(stream_llm([], "sarvam-30b", "bad", client=client))
