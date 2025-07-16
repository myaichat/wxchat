
###############################################################################
# fastapi_chat_proxy.py  – clean version (no inspect/eval!)                   #
###############################################################################

import json
import os
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import websockets

from streaming_chat_fixed import send_message_with_streaming   # ← fixed import

# ------------------------------------------------------------------
WS_URL = os.getenv(
    "CHATGPT_DEVTOOLS_WS",
    "ws://localhost:9222/devtools/page/88E0A660C0870B92DD1E7248EDABA645",
)
# ------------------------------------------------------------------

app = FastAPI(title="ChatGPT DevTools Proxy")


class ChatRequest(BaseModel):
    message: str
    timeout: int | None = 60


async def event_stream(message: str, timeout: int) -> AsyncGenerator[bytes, None]:
    """Server‑Sent‑Events wrapper around send_message_with_streaming()."""
    async for chunk in send_message_with_streaming(message, timeout):
        yield (json.dumps(chunk) + "\n").encode("utf-8")


@app.post("/ask-chatgpt")
async def ask_chatgpt(req: ChatRequest):
    try:
        return StreamingResponse(
            event_stream(req.message, req.timeout),
            media_type="text/event-stream",
        )
    except websockets.InvalidURI as e:
        raise HTTPException(500, f"Bad WebSocket URI: {e}")
    except Exception as e:
        raise HTTPException(500, str(e))


# --- optional CLI quick‑test -----------------------------------------------
if __name__ == "__main__":
    import sys, uvicorn, requests

    if len(sys.argv) == 2:
        payload = {"message": sys.argv[1]}
        with requests.post("http://localhost:8000/ask-chatgpt", json=payload, stream=True) as r:
            for line in r.iter_lines():
                if line:
                    print(json.loads(line))
    else:
        uvicorn.run(app, host="127.0.0.1", port=8002)
