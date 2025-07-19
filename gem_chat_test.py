#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gem_chat_test.py  —  Ask Google Gemini in an already‑open Chrome tab
via DevTools WebSocket (no target discovery needed).

Prereqs:
    pip install websocket-client
Run:
    chrome.exe --remote-debugging-port=9222
    # open https://gemini.google.com/app and log in
    python gem_chat_test.py "Explain CRDTs in one paragraph."
"""

import json
import sys
import time
from typing import Optional

import websocket

# ── Only change these if your environment differs ─────────────────────────────
WS_URL      = "ws://localhost:9222/devtools/page/8D25B8EDED124ED7635252EF0F0E4217"
SOCKET_TO   = 5          # seconds for each WebSocket read
POLL_EVERY  = 1.0        # seconds between DOM polls
MAX_WAIT    = 45         # overall timeout in seconds
# Selectors – update if Google tweaks markup
TEXTAREA_JS = "document.querySelector('.ql-editor:not(.ql-clipboard)')"          # Gemini input box
AI_MSGS_JS  = "document.querySelectorAll('div[data-message-author=\"ai\"]')"  # AI replies
# ──────────────────────────────────────────────────────────────────────────────


class CDP:
    """Minimal Chrome DevTools Protocol helper over WebSocket."""

    def __init__(self, ws_url: str):
        self.ws = websocket.create_connection(ws_url, timeout=SOCKET_TO)
        self.msg_id = 0
        self.call("Runtime.enable")  # enable Runtime domain up‑front

    def close(self):
        self.ws.close()

    def call(self, method: str, params: Optional[dict] = None):
        """Send CDP command and return raw reply."""
        self.msg_id += 1
        self.ws.send(json.dumps({
            "id": self.msg_id,
            "method": method,
            "params": params or {}
        }))
        while True:
            reply = json.loads(self.ws.recv())
            if reply.get("id") == self.msg_id:          # ignore events
                return reply

    def eval(self, js_src: str):
        """Evaluate JS, returning its primitive value or None if undefined."""
        res = self.call("Runtime.evaluate", {
            "expression": js_src,
            "returnByValue": True
        })["result"]
        return res.get("value")   # Key absent -> JS produced 'undefined'


def inject_prompt(cdp: CDP, prompt: str):
    """Type the prompt into Gemini and press Enter."""
    js = (
        f"( () => {{"
        f"  const box = {TEXTAREA_JS};"
        f"  if (!box) return 'NO_INPUT';"
        f"  box.focus();"
        f"  box.innerText = {json.dumps(prompt)};"
        f"  box.dispatchEvent(new Event('input', {{ bubbles: true }}));"
        f"  box.dispatchEvent(new KeyboardEvent('keydown', {{"
        f"        bubbles: true, cancelable: true, key:'Enter', code:'Enter', which:13"
        f"  }}));"
        f"  return 'OK';"
        f"}} )()"
    )
    if cdp.eval(js) != "OK":
        raise RuntimeError(
            "❌ Could not find Gemini text box – selector may be outdated."
        )


def latest_ai(cdp: CDP) -> str:
    """Get the text of the most recent AI message ('' if none yet)."""
    js = (
        f"( () => {{"
        f"  const msgs = Array.from({AI_MSGS_JS});"
        f"  return msgs.length ? msgs.at(-1).innerText.trim() : '';"
        f"}} )()"
    )
    return cdp.eval(js) or ""   # None → ""


def ask_gemini(prompt: str) -> str:
    """Send a question and wait for a full answer, streaming progress."""
    cdp = CDP(WS_URL)
    try:
        baseline = latest_ai(cdp)
        inject_prompt(cdp, prompt)

        start_time = time.time()
        last_shown = ""
        while time.time() - start_time < MAX_WAIT:
            answer = latest_ai(cdp)
            if answer and answer != baseline:
                if answer != last_shown:
                    print("…", answer.replace("\n", " ")[:100], end="\r")
                    last_shown = answer
                # crude completeness test: ends in sentence & ≥1 blank line
                if answer.endswith((".", "!", "?")) and "\n\n" in answer:
                    return answer
            time.sleep(POLL_EVERY)
        raise TimeoutError("⏰ Gemini did not finish within time limit.")
    finally:
        cdp.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gem_chat_test.py \"Your question here\"")
        sys.exit(1)

    prompt = " ".join(sys.argv[1:])
    print("🗨️  Asking Gemini →", prompt)
    try:
        reply = ask_gemini(prompt)
        print("\n\n🤖 Gemini says:\n", reply)
    except Exception as exc:
        print("❌", exc)
