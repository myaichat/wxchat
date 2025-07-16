#!/usr/bin/env python
"""
ask_chatgpt.py  –  call /ask-chatgpt and stream the reply

Usage:
    python ask_chatgpt.py "Your prompt here"
"""

import json
import sys
import requests
import io

# Fix Windows console encoding issues
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

URL = "http://localhost:8002/ask-chatgpt"
TIMEOUT_SEC = 60


def safe_print(text, end="\n", flush=False):
    """Print text with Unicode error handling for Windows console"""
    try:
        print(text, end=end, flush=flush)
    except UnicodeEncodeError:
        # Replace problematic Unicode characters with safe alternatives
        safe_text = text.replace("🚀", "[ROCKET]").replace("✅", "[CHECK]").replace("❌", "[X]")
        print(safe_text, end=end, flush=flush)


def stream_chat(prompt: str):
    payload = {"message": prompt, "timeout": TIMEOUT_SEC}

    # stream=True lets us iterate over server‑sent event lines as they arrive
    with requests.post(URL, json=payload, stream=True) as resp:
        resp.raise_for_status()

        previous = ""
        response_started = False
        
        for raw in resp.iter_lines(decode_unicode=True):
            if not raw:          # skip keep‑alives / blank lines
                continue

            try:
                data = json.loads(raw)
                status, content = data["status"], data["content"]
                

                if status == "started":
                    safe_print("🚀  assistant started typing\n")
                    response_started = True
                elif status == "streaming":
                    # Only show the newly arrived chunk
                    if len(content) > len(previous):
                        new_chunk = content[len(previous):]
                        safe_print(new_chunk, end="", flush=True)
                        previous = content
                elif status == "complete":
                    # Always show server‑supplied final text (may repeat a few chars)
                    if len(content) > len(previous):
                        remaining = content[len(previous):]
                        safe_print(remaining, end="", flush=True)
                    elif not response_started:
                        # If we never got streaming updates, show the complete content
                        safe_print(content, end="", flush=True)
                    safe_print("\n\n✅  complete")
                    break
                elif status in ["timeout", "error"]:
                    safe_print(f"\n❌  {status}: {content}")
                    break
                    
            except json.JSONDecodeError as e:
                safe_print(f"\n❌  JSON decode error: {e}")
                continue
            except Exception as e:
                safe_print(f"\n❌  Unexpected error: {e}")
                continue


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ask_chatgpt.py \"Your prompt here\"")
        sys.exit(1)

    stream_chat(sys.argv[1])
