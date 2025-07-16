"""
streaming_chat.py — send a prompt to an open ChatGPT tab (DevTools) and
stream the assistant’s reply.

    python streaming_chat.py "Hello, world"
"""

from __future__ import annotations
import asyncio, json, websockets


# ───────────────────────────── helpers ────────────────────────────────────
async def _wait_for_cmd_response(ws: websockets.WebSocketClientProtocol, cmd_id: int):
    while True:
        raw = await ws.recv()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if data.get("id") == cmd_id:
            return data
        if data.get("method") == "Runtime.consoleAPICalled":
            args = data.get("params", {}).get("args", [])
            if args:
                msg = args[0].get("value", "")
                if not msg.startswith(
                    ("RESPONSE_UPDATE:", "CONTENT_DEBUG:", "VALIDATION_DEBUG:",
                     "COMPLETION_DEBUG:", "COMPLETION_CHECK:")
                ):
                    print(f"Console: {msg}")


# ───────────────────────── streaming generator ────────────────────────────
import asyncio, json, textwrap, websockets

async def send_message_with_streaming(
    message: str,
    timeout: int = 60,
    ws_url: str | None = None,
):
    """
    Yields: {"status": "started" | "streaming" | "complete" | "timeout" | "error",
             "content": str}
    """
    ws_url = ws_url or "ws://localhost:9222/devtools/page/88E0A660C0870B92DD1E7248EDABA645"

    try:
        async with websockets.connect(ws_url) as websocket:
            # Enable Runtime domain
            await websocket.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
            await _wait_for_cmd_response(websocket, 1)

            # ── JavaScript observer, *no* f‑string braces to escape ──
            observer_js = textwrap.dedent("""
                (async function () {
                    if (window.chatObserverActive) {
                        console.log("Observer already active, skipping");
                        return "Observer already running";
                    }
                    window.chatObserverActive = true;

                    let messageSent = false,
                        responseFound = false,
                        responseComplete = false,
                        lastResponseText = "",
                        responseElement = null;

                    function extractText(el) {
                        if (!el) return "";
                        let t = el.innerText || el.textContent || "";
                        if (!t.trim()) t = [...el.querySelectorAll("p,div,span,pre,code")]
                                            .map(e => e.textContent).join(" ");
                        return t.trim();
                    }
                    function getResponseContent(el) {
                        let txt = extractText(el);
                        ["ChatGPT said:","Claude said:","Assistant:","AI:","Bot:"]
                          .forEach(p => { if (txt.startsWith(p)) txt = txt.slice(p.length).trim(); });
                        txt = txt.replace(/^[A-Za-z]+\\s+said:\\s*/, "").trim();
                        return txt;
                    }
                    function isAssistantMessage(el) {
                        if (el.querySelector('[data-message-author-role="assistant"]') ||
                            el.matches('[data-message-author-role="assistant"]')) return true;
                        const hints = ['.assistant-message','[data-author="assistant"]',
                                       '[data-role="assistant"]','[data-testid*="assistant"]'];
                        for (const h of hints) if (el.querySelector(h) || el.matches(h)) return true;
                        const txt = getResponseContent(el);
                        return txt && txt.length > 10 && !txt.includes("__PROMPT__") && messageSent;
                    }
                    function hasCompletionButtons(el) {
                        const primary = ['button[aria-label*="Copy"]',
                                         'button[data-testid*="copy"]',
                                         '[data-testid="copy-turn-action-button"]',
                                         'button[title*="Copy"]',
                                         'button[aria-label="Copy message"]',
                                         'button[aria-label="Regenerate response"]'];
                        return primary.some(sel => el.querySelector(sel));
                    }

                    /* mutation observer for new assistant node */
                    const topObserver = new MutationObserver(muts => {
                        if (!messageSent || responseFound) return;
                        muts.forEach(m => {
                            m.addedNodes.forEach(n => {
                                if (n.nodeType !== Node.ELEMENT_NODE) return;
                                if (isAssistantMessage(n)) {
                                    responseFound = true;
                                    responseElement = n;
                                    console.log("RESPONSE_STARTED");
                                    const init = getResponseContent(n);
                                    if (init.length > 5) {
                                        lastResponseText = init;
                                        console.log("RESPONSE_UPDATE:" + init);
                                    }
                                    /* inner observer for streaming chars */
                                    const inner = new MutationObserver(() => {
                                        const cur = getResponseContent(responseElement);
                                        if (cur !== lastResponseText) {
                                            lastResponseText = cur;
                                            console.log("RESPONSE_UPDATE:" + cur);
                                        }
                                    });
                                    inner.observe(responseElement,
                                                  { childList: true, subtree: true, characterData: true });
                                }
                            });
                        });
                    });
                    topObserver.observe(document.body, { childList: true, subtree: true });

                    /* 2‑second stability completion check */
                    let prevLen = 0, stableMs = 0;
                    const POLL = 250, STABLE = 2000;
                    const timer = setInterval(() => {
                        if (responseComplete || !responseElement) return;
                        const txt = getResponseContent(responseElement);
                        const same = txt.length === prevLen;
                        prevLen = txt.length;
                        stableMs = same ? stableMs + POLL : 0;
                        if (hasCompletionButtons(responseElement) && stableMs >= STABLE) {
                            responseComplete = true;
                            console.log("RESPONSE_COMPLETE:" + txt);
                            clearInterval(timer);
                            window.chatObserverActive = false;
                        }
                    }, POLL);

                    /* fill prompt, click Send */
                    const box = document.querySelector(
                        '#prompt-textarea,textarea[placeholder*="Message"],div[contenteditable="true"]');
                    if (!box) return "Textarea not found";
                    if (box.contentEditable === "true") box.innerHTML = "__PROMPT__";
                    else { box.value = "__PROMPT__";
                           box.dispatchEvent(new Event('input', { bubbles: true })); }
                    const send = document.querySelector(
                        'button[data-testid="send-button"],button[aria-label*="Send"],button[type="submit"]');
                    if (!send) return "Send button not found";
                    messageSent = true;
                    send.click();
                    return "Observer active";
                })();
            """)

            # ── inject the prompt safely ──
            js_payload = observer_js.replace("__PROMPT__", message.replace('"', '\\"'))

            await websocket.send(json.dumps({
                "id": 3, "method": "Runtime.evaluate",
                "params": {"expression": js_payload, "returnByValue": True}
            }))
            await _wait_for_cmd_response(websocket, 3)

            # ── listen for streaming console events ──
            start = asyncio.get_running_loop().time()
            response_started = False
            while (asyncio.get_running_loop().time() - start) < timeout:
                try:
                    raw = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(raw)
                except (asyncio.TimeoutError, json.JSONDecodeError):
                    continue

                if data.get("method") != "Runtime.consoleAPICalled":
                    continue
                msg = data["params"]["args"][0]["value"]

                if msg == "RESPONSE_STARTED":
                    response_started = True
                    yield {"status": "started", "content": ""}
                elif msg.startswith("RESPONSE_UPDATE:") and response_started:
                    yield {"status": "streaming", "content": msg[len("RESPONSE_UPDATE:") :]}
                elif msg.startswith("RESPONSE_COMPLETE:"):
                    yield {"status": "complete", "content": msg[len("RESPONSE_COMPLETE:") :]}
                    break
                elif msg.startswith("TIMEOUT:"):
                    yield {"status": "timeout", "content": ""}
                    break
            else:
                yield {"status": "timeout", "content": ""}

    except Exception as e:
        yield {"status": "error", "content": str(e)}



# ─────────────────────── convenience wrapper ───────────────────────────────
async def send_message_with_observer(message: str, timeout: int = 60,
                                     ws_url: str | None = None) -> str:
    final = None
    async for chunk in send_message_with_streaming(message, timeout, ws_url):
        if chunk["status"] in ("complete", "timeout", "error"):
            final = chunk["content"]
            break
    return final or "No response received"


# ───────────────────────────── CLI demo ────────────────────────────────────
if __name__ == "__main__":
    import sys

    async def _demo():
        prompt = " ".join(sys.argv[1:]) or "Hello! Tell me more about dbt"
        prev = ""
        async for ch in send_message_with_streaming(prompt):
            st, txt = ch["status"], ch["content"]
            if st == "started":
                print("\n🚀 streaming...\n")
            elif st == "streaming":
                print(txt[len(prev):], end="", flush=True)
                prev = txt
            elif st == "complete":
                print(txt[len(prev):], end="", flush=True)
                print("\n\n✅ complete")
                break
            else:
                print(f"\n❌ {st}: {txt}")
                break

    asyncio.run(_demo())
