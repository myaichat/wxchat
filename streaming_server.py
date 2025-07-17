
###############################################################################
# fastapi_chat_proxy.py  – clean version (no inspect/eval!)                   #
###############################################################################

import json
import os
from typing import AsyncGenerator
from datetime import datetime

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

def save_chat_log(question: str, answer: str, model: str = "gpt-4o"):
    """Save individual chat session to timestamped JSON file"""
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Create timestamp for filename and log entry
    timestamp = datetime.now()
    filename_timestamp = timestamp.strftime("%Y%m%d_%H%M%S")
    iso_timestamp = timestamp.isoformat()
    
    # Create log entry
    log_entry = {
        "timestamp": iso_timestamp,
        "question": question,
        "answer": answer,
        "model": model
    }
    
    # Save to individual timestamped file
    filename = f"logs/server_chat_session_{filename_timestamp}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(log_entry, f, ensure_ascii=False, indent=2)
    
    print(f"Chat session logged to: {filename}")
    return filename

app = FastAPI(title="ChatGPT DevTools Proxy")


class ChatRequest(BaseModel):
    message: str
    timeout: int | None = 60


async def event_stream(message: str, timeout: int) -> AsyncGenerator[bytes, None]:
    """Server‑Sent‑Events wrapper around send_message_with_streaming() with logging."""
    complete_answer = ""
    
    async for chunk in send_message_with_streaming(message, timeout):
        # Yield the chunk for streaming response
        yield (json.dumps(chunk) + "\n").encode("utf-8")
        
        # Collect the complete answer for logging
        if chunk.get("status") == "complete":
            complete_answer = chunk.get("content", "")
            # Save the complete conversation to log
            try:
                save_chat_log(message, complete_answer)
            except Exception as e:
                print(f"Error saving chat log: {e}")
        elif chunk.get("status") == "error":
            complete_answer = f"Error: {chunk.get('content', 'Unknown error')}"
            try:
                save_chat_log(message, complete_answer)
            except Exception as e:
                print(f"Error saving chat log: {e}")


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
        complete_response = ""
        
        print(f"Sending message: {sys.argv[1]}")
        print("=" * 50)
        
        with requests.post("http://localhost:8002/ask-chatgpt", json=payload, stream=True) as r:
            for line in r.iter_lines():
                if line:
                    chunk = json.loads(line)
                    print(chunk)
                    
                    # Collect complete response for CLI logging
                    if chunk.get("status") == "complete":
                        complete_response = chunk.get("content", "")
                        
        print("=" * 50)
        if complete_response:
            print(f"Complete response logged. Length: {len(complete_response)} characters")
    else:
        print("Starting ChatGPT DevTools Proxy server on http://127.0.0.1:8002")
        print("Logs will be saved to the 'logs/' directory")
        uvicorn.run(app, host="127.0.0.1", port=8002)
