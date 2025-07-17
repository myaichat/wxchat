# test_chat_proxy.py
# ---------------------------------------------------------------------------
# Requirements:
#   pip install pytest httpx[http2] fastapi
#   (You already have fastapi and its deps because of the server)
#
# Test strategy:
#   • Patch send_message_with_streaming → yield a deterministic sequence
#   • Issue POST /ask-chatgpt with TestClient (built into FastAPI)
#   • Collect streamed JSON lines and assert they match expectations
# ---------------------------------------------------------------------------
import json
from fastapi.testclient import TestClient
import pytest

# Import the FastAPI app **after** pytest is running so monkey‑patching works
import fastapi_chat_proxy as chat_proxy  # rename if your file is different


@pytest.fixture(scope="module")
def client():
    return TestClient(chat_proxy.app)


def fake_stream(_message: str, _timeout: int):
    """Deterministic replacement for send_message_with_streaming()"""
    async def _gen():
        yield {"status": "started", "content": ""}
        yield {"status": "streaming", "content": "Hello"}
        yield {"status": "streaming", "content": "Hello World"}
        yield {"status": "complete", "content": "Hello World"}
    return _gen()


def test_streaming_endpoint(monkeypatch, client):
    # 1️⃣ Replace the real WebSocket generator with our fake one
    monkeypatch.setattr(
        chat_proxy, "send_message_with_streaming", fake_stream, raising=True
    )

    # 2️⃣ Hit the endpoint (stream=True lets us iterate over the body)
    resp = client.post(
        "/ask-chatgpt",
        json={"message": "Hi", "timeout": 5},
        stream=True,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    # 3️⃣ Collect streamed JSON objects
    chunks = [json.loads(line) for line in resp.iter_lines() if line]

    # 4️⃣ Assert the flow is correct
    assert chunks[0]["status"] == "started"
    assert chunks[1]["status"] == "streaming"
    assert chunks[-1] == {"status": "complete", "content": "Hello World"}
