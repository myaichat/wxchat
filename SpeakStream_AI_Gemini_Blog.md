# SpeakStream AI: Multi-Model Voice Chat in One File
**A thread-safe Streamlit voice recorder that streams to ChatGPT, Claude, Grok, Perplexity & Gemini—simultaneously**

![SpeakStream AI Multi-Model Interface](screenshot.png)

## TL;DR
`gemini_model_chat_app.py` is a *single* Streamlit script that:

1. Records 16 kHz voice in a background thread (zero UI blocking).  
2. Saves each recording as a timestamped `.wav` file.  
3. Auto-transcribes with OpenAI Whisper (or manual editing).  
4. Fires your question to **all five** major AI models—ChatGPT, Claude, Grok, Perplexity & Gemini—concurrently.  
5. Streams responses back into separate tabs, side-by-side for instant comparison.  
6. Maintains thread safety with `streamlit.runtime.scriptrunner.add_script_run_ctx` and centralized refresh loops.

If you want a *production-grade*, real-time voice chat lab for comparing AI models, copy the file, configure your `.env`, and run:

```bash
pip install -r requirements.txt
streamlit run gemini_model_chat_app.py
```

## Why This Multi-Model Approach?

**Single interface, multiple perspectives.** Most voice AI demos focus on one model; SpeakStream fans out to five vendors simultaneously, letting you compare responses in real-time.

**Thread safety first.** Mixing `sounddevice`, Streamlit UI updates, and async LLM streams is a concurrency nightmare without proper isolation—this script demonstrates clean patterns.

**Immediate extensibility.** Each model lives in its own `/chat_handlers/*_handler.py`. Adding a sixth model takes minutes, not hours.

**Smart auto-triggering.** Enable "Auto" mode for any model and responses start streaming the moment transcription completes.

## High-Level Architecture

| Layer | Key Components | Notes |
|-------|---------------|-------|
| **UI & Session State** | `st.tabs`, model checkboxes, 200+ state flags | Fine-grained on/off per model & auto-actions |
| **Audio Capture** | `record_worker`, `save_wav` | Daemon thread, dumps PCM to queue → WAV |
| **Transcription** | `Transcribe` wrapper | OpenAI Whisper API with object reuse |
| **LLM Handlers** | `*_start_concurrent_streaming`, `render_*_responses` | One module per model, dual streams (WebUI + API) |
| **Central Loop** | `handle_all_streaming()` | Polls every 200ms, manages completion flags, logs Q&A pairs |
| **Logging** | JSON per session & model | `logs/gemini/gemini_session_YYYYMMDD_HHMMSS.json`, etc. |

## Deep Dive: Thread-Safe Building Blocks

### 1. Background Audio Recording
```python
def record_worker(stop_evt: threading.Event,
                  audio_q: queue.Queue,
                  frames: list[np.ndarray]):
    """Runs in background; NEVER touches streamlit objects."""
    def _callback(indata, *_):
        audio_q.put(indata.copy())

    with sd.InputStream(samplerate=RATE, channels=CH, dtype="int16",
                        callback=_callback):
        while not stop_evt.is_set():
            try:
                frames.append(audio_q.get(timeout=0.1))
            except queue.Empty:
                pass  # nothing yet
```

- **No Streamlit calls inside**—just pure audio I/O
- **Clean shutdown** via `stop_evt.set()` from UI thread
- **16kHz mono** optimized for voice recognition

### 2. Safe UI Updates from Background Threads
```python
def start_thread(fn, *args, **kwargs):
    """Utility – start a daemon thread that can call Streamlit commands."""
    th = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    add_script_run_ctx(th)  # <-- the magic line
    th.start()
    return th
```

`add_script_run_ctx` injects the current ScriptRunContext into the thread, enabling safe `st.*` calls from background handlers that stream tokens back to the UI.

### 3. Centralized Streaming Orchestrator
Instead of scattered `st.rerun()` calls, one master loop:

```python
def handle_all_streaming():
    """Centralized handler for all streaming activities"""
    any_streaming = False
    
    # Check each model's streaming status
    if st.session_state.gemini_concurrent_streaming_active:
        any_streaming = True
        if (st.session_state.gemini_webui_stream_complete and 
            st.session_state.gemini_api_stream_complete):
            st.session_state.gemini_concurrent_streaming_active = False
            log_qa_pair(...)  # Save to JSON
            st.success("✅ Gemini responses completed!")
    
    # Repeat for chatgpt, claude, grok, perplexity...
    
    if any_streaming:
        time.sleep(0.2)  # 200ms refresh rate
        st.rerun()
```

This prevents race conditions and UI flicker while maintaining smooth streaming updates.

## Model Handler Architecture

Each AI model follows the same pattern with four key functions:

### Example: Gemini Handler Structure
```python
# chat_handlers/gemini_handler.py

def start_concurrent_streaming(question):
    """Initiates both WebUI and API streams"""
    if st.session_state.enable_gemini_webui:
        start_thread(handle_concurrent_streaming, question, "webui")
    if st.session_state.enable_gemini_api:
        start_thread(handle_concurrent_streaming, question, "api")

def render_gemini_responses():
    """Displays streaming responses in UI columns"""
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🌐 Gemini Web UI**")
        if st.session_state.gemini_webui_streaming_text:
            st.markdown(st.session_state.gemini_webui_streaming_text)
    
    with col2:
        st.markdown("**🔌 Gemini API**")
        if st.session_state.gemini_api_streaming_text:
            st.markdown(st.session_state.gemini_api_streaming_text)

def handle_concurrent_streaming(question, stream_type):
    """Background thread that pushes tokens to session state"""
    # Import the actual streaming implementation
    from .gemini_streaming_chat import stream_gemini_response
    
    for chunk in stream_gemini_response(question, stream_type):
        if st.session_state.stop_streaming:
            break
        # Update appropriate session state variable
        st.session_state[f"gemini_{stream_type}_streaming_text"] += chunk

def handle_stopped_streaming():
    """Cleanup when user hits stop button"""
    if st.session_state.stop_streaming:
        # Reset all streaming flags
        st.session_state.gemini_concurrent_streaming_active = False
        # ... cleanup logic
```

## Using the App

### 1. **Configure Models**
Check WebUI and/or API boxes for each AI service you want to use:
- **💬 ChatGPT**: WebUI + API
- **🤖 Claude**: WebUI + API  
- **🚀 Grok**: WebUI + API
- **🔍 Perplexity**: WebUI + API
- **💎 Gemini**: WebUI + API (enabled by default)

### 2. **Set Auto-Options**
Enable "Auto" checkboxes to start streaming immediately after transcription:
- 🤖 Auto-transcribe after recording
- 🤖 Auto ChatGPT, Auto Claude, Auto Grok, etc.

### 3. **Record & Compare**
1. Press **▶️ Start** → speak your question → press **⏹️ Stop**
2. Audio auto-transcribes (or edit manually)
3. Press **💬 Get AI Response** or let auto-mode handle it
4. Watch responses stream into separate tabs for instant comparison

### 4. **Edit & Retry**
Tweak the transcription text box and hit **Ctrl + Enter** to re-query all enabled models with your refined question.

## Smart Features

### Auto-Triggering Logic
```python
# Perplexity has special "immediate start" behavior
if (st.session_state.enable_perplexity_api and 
    st.session_state.transcription and 
    not st.session_state.recording):
    
    question = current_transcription()
    if (question and not st.session_state.perplexity_concurrent_streaming_active):
        st.session_state.perplexity_processed_transcription = question
        perplexity_start_concurrent_streaming(question)
        st.rerun()
```

### Session Logging
Each model maintains its own conversation log:
```json
{
  "timestamp": "2024-01-15T14:30:22",
  "question": "What's the weather like today?",
  "webui_response": "Based on current conditions...",
  "api_response": "The weather today is...",
  "model": "gemini-pro"
}
```

### Thread-Safe State Management
200+ session state variables track everything:
- Recording status, transcription text
- Per-model streaming flags, response buffers
- Auto-mode settings, conversation histories
- Logging file paths, completion states

## Extending to a New Model

Adding a sixth AI model takes three steps:

### 1. Create Handler Module
```python
# chat_handlers/your_model_handler.py
def start_concurrent_streaming(question):
    # Start WebUI and/or API streams
    
def render_your_model_responses():
    # Display streaming responses in columns
    
def handle_concurrent_streaming(question, stream_type):
    # Background streaming logic
    
def handle_stopped_streaming():
    # Cleanup on stop
```

### 2. Add Session State Variables
```python
# In main app file
if "your_model_concurrent_streaming_active" not in st.session_state:
    st.session_state.your_model_concurrent_streaming_active = False
if "your_model_webui_streaming_text" not in st.session_state:
    st.session_state.your_model_webui_streaming_text = ""
# ... add all necessary state variables
```

### 3. Wire UI Components
```python
# Add to model selection section
with ai_col6:
    st.markdown("**🆕 Your Model**")
    your_model_col1, your_model_col2 = st.columns(2)
    with your_model_col1:
        st.session_state.enable_your_model_webui = st.checkbox("WebUI", key="your_model_webui")
    with your_model_col2:
        st.session_state.enable_your_model_api = st.checkbox("API", key="your_model_api")

# Add to tabs section
if st.session_state.enable_your_model_webui or st.session_state.enable_your_model_api:
    tab_names.append("🆕 Your Model")

# Add to centralized streaming handler
if st.session_state.your_model_concurrent_streaming_active:
    any_streaming = True
    # ... completion logic
```

## Performance Tips

**Batch token updates**: Flush UI every ~20 tokens instead of per-token for smoother, less CPU-intensive streaming.

**Local Whisper**: For heavy transcription workloads, run `openai/whisper-tiny` locally on GPU to reduce API latency.

**Selective model enabling**: Only enable models you're actively comparing to reduce resource usage.

**Chrome debugging**: The WebUI handlers assume Chrome running with `--remote-debugging-port=9222` for scraping responses without API costs.

## Technical Highlights

### CSS Styling
Custom CSS ensures proper text wrapping and tab transparency:
```css
.stMarkdown {
    word-wrap: break-word !important;
    overflow-wrap: break-word !important;
    max-width: 100% !important;
    overflow-x: hidden !important;
}
```

### Audio Configuration
```python
RATE, CH = 16_000, 1  # 16kHz mono for optimal voice recognition
OUT_DIR = "recordings"  # Timestamped WAV files
TIMEOUT_SEC = 60  # Max recording length
```

### Logging Structure
```
logs/
├── chatgpt/chatgpt_session_20240115_143022.json
├── claude/claude_session_20240115_143022.json
├── grok/grok_session_20240115_143022.json
├── perplexity/perplexity_session_20240115_143022.json
└── gemini/gemini_session_20240115_143022.json
```

## Roadmap

🔄 **Streaming audio upload** → S3 for long-form conversations  
🖼️ **Screenshot-to-prompt** for multimodal questions  
🔬 **A/B scoring widget** → vote best answer, export to CSV  
📈 **Metrics dashboard** → latency & token-per-second charts  
🎯 **Custom model endpoints** → support for local LLMs  
🔊 **Text-to-speech** → hear responses back  

## Installation & Setup

1. **Clone and install dependencies**:
```bash
git clone <repository>
cd ui_interview_copilot
pip install -r requirements.txt
```

2. **Configure environment**:
```bash
cp .env.template .env
# Add your API keys for each service
```

3. **Start Chrome with debugging** (for WebUI features):
```bash
chrome --remote-debugging-port=9222
```

4. **Run the app**:
```bash
streamlit run gemini_model_chat_app.py
```

## One-Word Hashtags
#streamlit #whisper #chatgpt #claude #grok #perplexity #gemini #python #audio #multimodal #threading #concurrent #voice #ai #comparison

---

**SpeakStream AI** transforms voice into insights across five AI models simultaneously. Whether you're researching, brainstorming, or just curious how different models approach the same question, this single-file solution delivers production-grade voice-to-AI streaming with the extensibility to grow with your needs.

Happy streaming & may your tokens flow smoothly! 🚀
