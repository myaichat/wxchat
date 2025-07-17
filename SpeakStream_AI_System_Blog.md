# Speak & Compare: Real-Time API vs Search-Enhanced ChatGPT Responses

*Record, transcribe, and compare ChatGPT answers from the API and the Search Powered Web UI side by side.*

---

## TL;DR

SpeakStream AI helps you record voice, transcribe with Whisper, and send the same prompt to two ChatGPT endpoints (API and Search Powered Web UI) to compare responses in real time:

* Record voice in the Streamlit app.
* Transcribe via OpenAI Whisper.
* Send prompt concurrently to:
  * **API**: OpenAI Chat Completions.
  * **Search Powered Web UI**: Browser injection and DOM streaming.
* View both answers side by side and stop any stream.
* Log all Q&A pairs in JSON for review.

## Why I Built This

We built SpeakStream AI to record voice, transcribe it, and instantly compare how ChatGPT answers the same question via the API versus the search-powered Web UI. This side-by-side setup highlights differences in speed, formatting, and content.

## System At A Glance

```
┌────────────────────────────────────────────────────────────┐
│                       SpeakStream AI                       │
├───────────────┬─────────────────────┬──────────────────────┤
│   Streamlit   │  FastAPI Proxy      │ Chrome DevTools WS   │
│  Frontend     │  (WebUI relay)      │  + Browser Injection │
│ (chat_app.py) │ (streaming_server)  │ (streaming_chat.py)  │
└──────┬────────┴───────────┬─────────┴──────────────┬──────┘
       │                    │                        │
       │                    └──────────────▶ Inject prompt into
       │                                      open ChatGPT tab;
       │                                      stream DOM text back
       │
       ├────────────────────────────────────▶ Direct OpenAI API
       │                                      stream (Chat Completions)
       │
       └────────────────────────────────────▶ JSON logging (Q/A)
```

**Three tiers; two answer feeds; one voice prompt.**

---

## Key Capabilities

| Capability                      | Where It Lives                                | Notes                                                                 |
| ------------------------------- | --------------------------------------------- | --------------------------------------------------------------------- |
| Voice capture                   | `chat_app.py`                                 | Uses `sounddevice` input stream; thread‑safe queue → WAV save.        |
| Auto / manual transcription     | `chat_app.py` + `Transcribe` wrapper          | Whisper; user‑editable text box before sending.                       |
| Dual streaming                  | `chat_app.py` threads                         | Launches *Search Powered Web UI* + *API* workers concurrently.        |
| Search Powered Web UI streaming | FastAPI → DevTools → DOM observer             | JS MutationObserver watches assistant reply; pushes incremental text. |
| API streaming                   | OpenAI client `stream=True`                   | Token deltas accumulated; cleaned for Unicode before display.         |
| Smart chunk display             | Session‑state diffing + breakpoint heuristics | Avoid mid‑token markdown breaks; show cursor ▌ during stream.         |
| Stop buttons                    | User interrupt flags                          | Graceful cancel across both feeds.                                    |
| JSON logging                    | Session + server logs                         | Timestamped Q/A for replay + analytics.                               |

---

## Recording & Saving Audio

Audio capture runs in a **background thread** so Streamlit's UI stays responsive. Incoming 16 kHz, mono int16 frames are queued, collected, then written to timestamped WAV on stop.

```python
def record_worker(stop_evt: threading.Event, audio_q: queue.Queue, frames: list[np.ndarray]):
    """Runs in background; NEVER touches streamlit objects."""
    def _callback(indata, *_):
        audio_q.put(indata.copy())
    
    with sd.InputStream(samplerate=RATE, channels=CH, dtype="int16", callback=_callback):
        while not stop_evt.is_set():
            try:
                frames.append(audio_q.get(timeout=0.1))
            except queue.Empty:
                pass
```

A helper `save_wav()` concatenates frames, writes header metadata, and returns the file path so the UI can: (1) play it back, (2) show save status, (3) kick off transcription.

---

## Transcription Flow

Once recording stops you can transcribe automatically (default) or on demand:

1. User stops recording.
2. WAV path captured; UI shows success.
3. If **Auto‑transcribe** checked → call Whisper via `Transcribe()` wrapper.
4. Result placed in an **editable text area** — the *user‑visible edit* is always treated as *source of truth* when sending to ChatGPT.

This edit step matters: live meetings are messy. Fix names, strip "uhhh," or add follow‑up instructions before sending downstream.

```python
def transcribe_audio_file(audio_path: str) -> str | None:
    """Transcribe audio file using OpenAI Whisper API."""
    try:
        if st.session_state.transcriber is None:
            st.session_state.transcriber = Transcribe()
        
        transcript = st.session_state.transcriber.transcribe_audio(audio_path)
        return transcript
    except Exception as e:
        st.error(f"Transcription failed: {str(e)}")
        return None
```

---

## Launching Dual Streams

When you submit the transcription form (Ctrl+Enter) or when auto‑ChatGPT triggers:

```python
def start_concurrent_streaming(question):
    """Start both Web UI and API streaming concurrently"""
    st.session_state.concurrent_streaming_active = True
    st.session_state.webui_streaming_text = ""
    st.session_state.api_streaming_text = ""
    st.session_state.webui_stream_complete = False
    st.session_state.api_stream_complete = False
    st.session_state.generating_response = True
    st.session_state.generating_api_response = True
    st.session_state.stop_streaming = False
    
    # Start Web UI streaming thread
    start_thread(webui_streaming_worker, question)
    
    # Start API streaming thread  
    start_thread(api_streaming_worker, question)
```

The UI flips into **comparison mode**: two columns labeled *Web UI* and *API*. Each worker streams incremental markdown into session state; Streamlit auto‑reruns on a short sleep for smooth updates.

---

## Search Powered Web UI Streaming (Browser Injection Path)

The Search Powered Web UI path routes through the FastAPI proxy, which calls a DevTools WebSocket client that injects JavaScript into a live ChatGPT tab. That JS does five jobs:

1. **Locate the chat textarea** and fill it with the prompt.
2. **Click the Send button** programmatically.
3. **Attach a MutationObserver** to the DOM to detect the assistant's new message node.
4. **Poll that node** for text changes; emit `RESPONSE_UPDATE:` console logs as the message grows.
5. **Detect completion** heuristically (copy button present, natural punctuation, or timeout) → emit `RESPONSE_COMPLETE:`.

```javascript
// Set up mutation observer for real-time response monitoring
window.chatMainObserver = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        if (mutation.type === 'childList') {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === Node.ELEMENT_NODE && !responseFound) {
                    if (isAssistantMessage(node)) {
                        responseFound = true;
                        responseElement = node;
                        console.log("RESPONSE_STARTED");
                        
                        // Monitor for streaming updates
                        window.chatStreamingPollId = setInterval(() => {
                            const currentContent = getResponseContent(responseElement);
                            if (currentContent !== lastResponseText) {
                                lastResponseText = currentContent;
                                console.log("RESPONSE_UPDATE:" + currentContent);
                            }
                        }, 50);
                    }
                }
            });
        }
    });
});
```

The Python side listens to DevTools `Runtime.consoleAPICalled` events, parses these markers, and yields structured streaming events: `started`, `streaming`, `complete`, `timeout`, or `error`.

Because we're scraping the rendered ChatGPT DOM, what you see is *exactly* what the hosted product shows — including formatting artifacts like **"markdown / Copy / Edit"** headers that sometimes ride along in the transcript. We strip these on display.

---

## API Streaming (Direct OpenAI Call)

In parallel, the API path calls the OpenAI client with `stream=True` on the selected model (default: `gpt-4o`). Each delta's `.content` is appended to a buffer; the UI shows the growing text with a cursor.

```python
def api_streaming_worker(question):
    """Worker thread for API streaming - updates session state incrementally"""
    try:
        from openai import OpenAI
        import os
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Store original prompt for logging and consistency
        original_prompt = question.strip()
        cleaned_prompt = original_prompt + ". Answer in clean raw markdown without citations."
        
        # Add to conversation history (separate copy for API)
        messages = st.session_state.conversation_history + [{"role": "user", "content": cleaned_prompt}]
        
        full_response = ""
        
        # Stream the response
        stream = client.chat.completions.create(
            model=st.session_state.selected_model,
            messages=messages,
            stream=True
        )
        
        st.session_state.api_streaming_text = "🚀 API started typing..."
        
        for chunk in stream:
            if st.session_state.stop_streaming:
                break
                
            if chunk.choices[0].delta.content is not None:
                full_response += chunk.choices[0].delta.content
                # Clean Unicode surrogates before displaying
                clean_response = full_response.encode('utf-8', errors='replace').decode('utf-8')
                # Update session state with cursor
                st.session_state.api_streaming_text = clean_response + "▌"
        
        # Final update without cursor
        clean_final_response = full_response.encode('utf-8', errors='replace').decode('utf-8')
        st.session_state.api_streaming_text = clean_final_response
        st.session_state.api_response = clean_final_response
        
        st.session_state.api_stream_complete = True
        st.session_state.generating_api_response = False
        
    except Exception as e:
        st.session_state.api_streaming_text = f"Error: {str(e)}"
        st.session_state.api_stream_complete = True
        st.session_state.generating_api_response = False
```

We also normalize Unicode (replace unpaired surrogates) so decoding errors don't crash Streamlit when emoji arrive mid‑token.

---

## Smart Chunking & Safe Breakpoints

Raw stream data is noisy. Updating the UI *every byte* flickers, but buffering too long makes the app feel frozen. SpeakStream AI uses **breakpoint heuristics**:

```python
safe_patterns = [
    '\n\n',  # Paragraph breaks
    '\n- ',  # List items  
    '\n## ', # Headers
    '\n### ', # Subheaders
    '. ',    # Sentence endings
    '! ',    # Exclamations
    '? ',    # Questions
    ', ',    # Commas
    '; ',    # Semicolons
    ': ',    # Colons
    '**.',   # Bold endings with period
    '**,',   # Bold endings with comma
    '**:',   # Bold endings with colon
    '`.',    # Code endings with period
    '`,',    # Code endings with comma
    '```\n', # Code block endings
]
```

* Paragraph double‑newline (`\n\n`)
* List markers (`\n- `)
* Markdown headers (`\n## `, `\n### `)
* Sentence punctuation (`. `, `! `, `? `)
* Graceful fallbacks: length thresholds + last safe space not inside `**bold**` or code fences.

Result: readable live text that rarely breaks formatting.

---

## Stop Controls & Completion Handling

Either feed can be interrupted via **🛑 Stop** buttons. Internally we flip a `stop_streaming` flag that workers check between chunks. When both feeds complete (or stop), the comparison session ends and the UI shows a ✅ summary.

```python
# Stop button for concurrent streaming - placed above columns
if st.session_state.concurrent_streaming_active:
    if st.button("🛑 Stop All Streaming"):
        st.session_state.stop_streaming = True
        st.session_state.concurrent_streaming_active = False
        st.session_state.generating_response = False
        st.session_state.generating_api_response = False
        st.rerun()
```

Completion detection differs by path:

* **Search Powered Web UI** relies on DOM stability + UI hints.
* **API** simply ends when the event stream closes.

---

## Side‑By‑Side: API vs Search Powered Web UI Comparison

We created this comparison to see how ChatGPT responds to the same question via the API and via the search-powered Web UI. Below are practical differences observed:

### 1. Latency Profile

* **Search Powered Web UI**: Extra overhead (DevTools roundtrip + DOM parse). First token later, but sometimes *burstier* once streaming starts.
* **API**: Lower startup latency; steady token cadence.

### 2. Content Fidelity

* **Search Powered Web UI** output may include UI cruft ("markdown", "Copy", action buttons) — remove or strip.
* **API** output is clean model text.

### 3. Model Drift / Product Layering

* Web ChatGPT may apply product‑side safety rewrites, tool triggers, or formatting wrappers.
* API returns raw model completions based on your message list.

### 4. Conversation Context

* Search Powered Web UI context = whatever is in the open browser conversation thread.
* API context = explicit `messages=[...]` you send; fully scriptable.

### 5. Streaming Granularity

* Search Powered Web UI updates arrive as **full accumulated text snapshots**; we diff against the last length to compute the new visible chunk.
* API updates arrive as **token deltas**; we simply append.

### 6. Unicode & Emoji Surprises

* Search Powered Web UI text is already DOM‑decoded; safe but may include invisible control characters.
* API deltas can surface half‑codepoints mid‑stream; we defensive‑encode before display.

### 7. Interrupt Behavior

* Stopping the Search Powered Web UI path tries to halt further UI updates but cannot cancel what the hosted ChatGPT already started.
* API stream can be aborted client‑side immediately; remaining tokens are dropped.

> **Takeaway:** Use Search Powered Web UI streaming when you want to *observe* the hosted ChatGPT product; use API streaming when you want *programmable, clean, low‑latency* text suitable for downstream automation.

---

## Logging Everything

Two levels of logging:

**Session Log (frontend):** Every user prompt + final assistant output (per model) appended as JSON lines to a timestamped file.

```python
def log_qa_pair(question: str, answer: str):
    """Log question/answer pair to session log file"""
    try:
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "question": question,
            "answer": answer,
            "model": st.session_state.selected_model
        }
        
        # Append to log file
        with open(st.session_state.session_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            
    except Exception as e:
        st.error(f"Failed to log Q&A pair: {str(e)}")
```

**Server Log (proxy):** Each Search Powered Web UI exchange logged individually when a `complete` or `error` event fires.

```python
def save_chat_log(question: str, answer: str, model: str = "gpt-4o"):
    """Save individual chat session to timestamped JSON file"""
    timestamp = datetime.now()
    filename_timestamp = timestamp.strftime("%Y%m%d_%H%M%S")
    
    log_entry = {
        "timestamp": timestamp.isoformat(),
        "question": question,
        "answer": answer,
        "model": model
    }
    
    filename = f"logs/server_chat_session_{filename_timestamp}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(log_entry, f, ensure_ascii=False, indent=2)
```

Because logs are UTF‑8 JSON, you can later build analytics — response length, latency, drift between feeds, transcription error rates, etc.

---

## Quickstart

### 1. Install deps (example)

```bash
pip install streamlit sounddevice fastapi uvicorn websockets openai python-dotenv
```

### 2. Env Vars

```bash
export OPENAI_API_KEY=sk-your-key
export CHATGPT_DEVTOOLS_WS="ws://localhost:9222/devtools/page/<YOUR_PAGE_ID>"
```

Launch Chrome with remote debugging:

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222
```

(Windows: adjust path; WSL users forward port.)

### 3. Start Servers

**Option A: Manual Start (Cross-platform)**
```bash
# Terminal A: FastAPI proxy (Search Powered Web UI relay)
python streaming_server.py

# Terminal B: Streamlit frontend
streamlit run chat_app.py
```

**Option B: Automated Start (Windows PowerShell)**

For Windows users, two PowerShell scripts automate the setup process:

**`start_streaming_server.ps1`** - Automated Server Management
```powershell
# Kill all running python processes
taskkill /F /IM python.exe

# Start the streaming server in a new cmd window
Start-Process cmd -ArgumentList "/k", "python streaming_server.py"

# Wait for port 8002 to open (up to 10 seconds)
$timeout = 20
$counter = 0
while (-not (netstat -an | findstr ':8002') -and $counter -lt $timeout) {
    Start-Sleep -Milliseconds 500
    $counter++
}

if ($counter -lt $timeout) {
    Write-Host "✅ Port 8002 is now open."
} else {
    Write-Host "❌ Port 8002 did not open in time."
}
```

This script:
- Kills any existing Python processes to avoid port conflicts
- Launches the FastAPI server in a new command window
- Monitors port 8002 until the server is ready
- Provides visual feedback on server status

**`start_chrome_debug.ps1`** - Chrome DevTools Setup
```powershell
# Kill only Chrome process using port 9222
$port9222Process = netstat -ano | findstr ':9222' | findstr 'LISTENING'
if ($port9222Process) {
    $pid = ($port9222Process -split '\s+')[-1]
    if ($pid) {
        Write-Host "🔄 Killing Chrome process on port 9222 (PID: $pid)"
        taskkill /F /PID $pid 2>$null
        Start-Sleep -Seconds 1
    }
}

# Start Chrome with remote debugging
$chromeArgs = @(
    "--remote-debugging-port=9222",
    "--user-data-dir=chrome-debug",
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    "--disable-backgrounding-occluded-windows"
)

Start-Process -FilePath "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList $chromeArgs

# Wait for port 9222 and get WebSocket URL
$timeout = 20
$counter = 0
while (-not (netstat -an | findstr ':9222') -and $counter -lt $timeout) {
    Start-Sleep -Milliseconds 500
    $counter++
}

if ($counter -lt $timeout) {
    Write-Host "✅ Port 9222 is now open."
    
    # Get the WebSocket debugger URL
    try {
        $response = curl -s http://localhost:9222/json
        if ($response) {
            $jsonData = $response | ConvertFrom-Json
            if ($jsonData.Count -gt 1) {
                $webSocketUrl = $jsonData[1].webSocketDebuggerUrl
                Write-Host "🔗 WebSocket Debugger URL: $webSocketUrl"
            }
        }
    } catch {
        Write-Host "💡 You can manually check: http://localhost:9222/json"
    }
}
```

This script:
- Intelligently kills only Chrome processes using port 9222
- Launches Chrome with remote debugging enabled
- Uses a dedicated user data directory to avoid conflicts
- Disables background throttling for better streaming performance
- Automatically retrieves and displays the WebSocket debugger URL
- Provides the exact URL needed for the `CHATGPT_DEVTOOLS_WS` environment variable

**Usage:**
```powershell
# Run both scripts in PowerShell
.\start_streaming_server.ps1
.\start_chrome_debug.ps1

# Then start Streamlit manually
streamlit run chat_app.py
```

### 4. Record & Compare

1. Click **▶️ Start** to capture audio.
2. Click **⏹️ Stop**.
3. Edit transcription text.
4. Hit **Ctrl+Enter** (or button) → launches **both feeds**.
5. Watch columns fill in real time.

---

## Interpreting the Comparison

Here's a simple workflow to evaluate WebUI vs API consistency:

1. Ask a **short factual** question ("What is dbt?") — check formatting differences.
2. Ask a **code generation** request — does Search Powered Web UI add commentary the API omits?
3. Ask a **long multi‑part** instruction — compare heading structure + bullet formatting.
4. Speak a **noisy transcript** full of filler words — which path cleans it better?
5. Interrupt mid‑stream — how cleanly does each recover?

Log results; diff answers; track anomalies.

---

## Internals Cheat‑Sheet

**Session State Keys** (selected):

* `recording` — are we currently capturing audio?
* `last_wav` — path to most recent recording.
* `transcription` / `transcription_display` — raw + edited text.
* `conversation_history` — accumulated chat messages (user + assistant) for API calls.
* `webui_streaming_text` / `api_streaming_text` — live buffers for each feed.
* `stop_streaming` — user‑triggered interrupt flag.
* `*_stream_complete` — completion toggles that collapse dual mode.

**Concurrency Pattern:** Lightweight helper `start_thread()` wraps `add_script_run_ctx()` to ensure each worker thread can safely update Streamlit session state without context loss.

```python
def start_thread(fn, *args, **kwargs):
    """Utility – start a daemon thread that can call Streamlit commands."""
    th = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    add_script_run_ctx(th)          # <- critical line
    th.start()
    return th
```

---

## Troubleshooting Tips

### No audio captured

* Mic permissions? Correct input device? Sample rate mismatch?

### Search Powered Web UI never responds

* Wrong `CHATGPT_DEVTOOLS_WS` page ID.
* ChatGPT tab not loaded / logged in.
* Selector drift (UI changed) — update query list in injected JS.

### API feed crashes on emoji

* Confirm UTF‑8 cleaning where deltas append.

### Double answers / stale context

* Clear or reset `conversation_history` when starting a fresh session.

---

## Extending SpeakStream AI

Ideas you can bolt on quickly:

* **Live mic streaming (continuous)** instead of record‑then‑send.
* **Auto language detection** → route to appropriate Whisper model.
* **Timestamps → subtitle tracks** (SRT / VTT) in logs.
* **Voice back from GPT** using TTS; auto‑mix with waveform display.
* **Multi‑model shootout**: add Anthropic Claude, local Llama, or AWS Bedrock.
* **Latency charting**: log chunk timestamps; plot WebUI vs API token arrival curve.

---

## What I Learned

Building a *dual‑feed* pipeline exposes subtle but important differences between ChatGPT the product and ChatGPT the API:

* UI layers matter — product polish adds noise when scraping.
* Structured APIs are friendlier for automation but hide UX context.
* Transcription quality + light prompt massaging ("Answer in clean raw markdown…") dramatically reduces cleanup time.
* Threaded streaming in Streamlit is totally doable if you isolate side‑effectful work and centralize session state updates.

---

## Repo Layout (suggested)

```
📁 speakstream/
├─ chat_app.py            # Streamlit frontend
├─ streaming_server.py    # FastAPI WebUI relay
├─ streaming_chat.py      # DevTools injector / streamer
├─ include/
│   └─ transcribe.py      # Whisper wrapper
├─ logs/                  # JSON Q/A logs
└─ recordings/            # WAV audio captures
```

---

## Closing

SpeakStream AI turns your mic into an AI lab bench: speak once, test twice. If you're experimenting with model behavior, prompt design, or UI scraping, a **dual‑stream voice harness** like this saves time, exposes drift, and gives you structured artifacts you can mine later.

Let me know what you'd like to tweak — add screenshots, trim sections, expand the WebUI vs API comparison, or wire in more models. Happy streaming! 🎙️🤖
