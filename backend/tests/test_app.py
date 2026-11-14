import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import main
from config import Settings


def make_settings(**overrides):
    base = {
        "sarvam_api_key": "test-key",
        "allowed_origins": ["http://localhost:5177"],
    }
    base.update(overrides)
    return Settings(**base)


@pytest.fixture
def client():
    return TestClient(main.app)


def test_health_reports_key_presence(client, monkeypatch):
    monkeypatch.setattr(main, "settings", make_settings())
    assert client.get("/health").json() == {"status": "ok", "sarvam_key": True}
    monkeypatch.setattr(main, "settings", make_settings(sarvam_api_key=None))
    assert client.get("/health").json()["sarvam_key"] is False


def test_ws_rejects_unknown_origin(client, monkeypatch):
    monkeypatch.setattr(main, "settings", make_settings())
    with (
        pytest.raises(WebSocketDisconnect) as exc,
        client.websocket_connect("/ws", headers={"origin": "https://evil.example"}),
    ):
        pass
    assert exc.value.code == 1008


def test_ws_rejects_unsupported_model(client, monkeypatch):
    monkeypatch.setattr(main, "settings", make_settings())
    with client.websocket_connect("/ws?llm_model=gpt-4") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "Error"
        assert "Unsupported LLM model" in msg["description"]


def test_ws_reports_missing_api_key(client, monkeypatch):
    monkeypatch.setattr(main, "settings", make_settings(sarvam_api_key=None))
    with client.websocket_connect("/ws", headers={"origin": "http://localhost:5177"}) as ws:
        assert ws.receive_json() == {"type": "Error", "description": "SARVAM_API_KEY not set"}


def test_origin_allowed(monkeypatch):
    monkeypatch.setattr(main, "settings", make_settings())
    assert main.origin_allowed(None)
    assert main.origin_allowed("http://localhost:5177")
    assert not main.origin_allowed("http://localhost:9999")
    monkeypatch.setattr(main, "settings", make_settings(allowed_origins=["*"]))
    assert main.origin_allowed("http://anything")


def test_add_user_turn_merges_unanswered_and_trims(monkeypatch):
    history = [{"role": "system", "content": "sys"}]
    main.add_user_turn(history, "hello")
    main.add_user_turn(history, "are you there")
    assert history[-1] == {"role": "user", "content": "hello are you there"}

    monkeypatch.setattr(main, "MAX_HISTORY_MESSAGES", 3)
    history.append({"role": "assistant", "content": "yes"})
    main.add_user_turn(history, "q2")
    history.append({"role": "assistant", "content": "a2"})
    main.add_user_turn(history, "q3")
    assert history[0]["role"] == "system"
    assert [m["content"] for m in history[1:]] == ["q2", "a2", "q3"]
