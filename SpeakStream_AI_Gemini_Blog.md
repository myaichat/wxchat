# Simultaneous Voice Chat with ChatGPT, Claude, Grok, Perplexity, Gemini—A Step‑by‑Step Guide
**Build a thread-safe Streamlit app that records your voice and streams responses from all 5 major AI models simultaneously**

![SpeakStream AI Multi-Model Interface](screenshot.png)

## What You'll Build

By the end of this guide, you'll have a single Streamlit application (`gemini_model_chat_app.py`) that:

✅ **Records your voice** in high-quality 16kHz audio  
✅ **Auto-transcribes** using OpenAI Whisper API  
✅ **Streams to 5 AI models** simultaneously: ChatGPT, Claude, Grok, Perplexity & Gemini  
✅ **Displays responses** in real-time tabs for instant comparison  
✅ **Logs conversations** to JSON files for each model  
✅ **Handles threading** safely without UI blocking  

**Time to complete:** 15-30 minutes  
**Skill level:** Intermediate Python/Streamlit  

## Quick Start

```bash
# Clone and setup
git clone <repository>
cd ui_interview_copilot
pip install -r requirements.txt

# Configure API keys
cp .env.template .env
# Edit .env with your API keys

# Start Chrome for WebUI features (optional)
chrome --remote-debugging-port=9222

# Run the app
streamlit run gemini_model_chat_app.py
```

## Step 1: Understanding the Architecture

The app uses a **modular handler pattern** where each AI model has its own dedicated module:

```
📁 chat_handlers/
├── chatgpt_handler.py      # ChatGPT WebUI + API
├── claude_handler.py       # Claude WebUI + API  
├── grok_handler.py         # Grok WebUI + API
├── perplexity_handler.py   # Perplexity WebUI + API
└── gemini_handler.py       # Gemini WebUI + API
```

**Key Components:**
- **Audio Recording**: Background thread captures voice without blocking UI
- **Transcription**: OpenAI Whisper converts speech to text
- **Concurrent Streaming**: All enabled models process simultaneously
- **Centralized State**: 200+ session variables manage everything
- **Thread Safety**: `add_script_run_ctx` enables safe UI updates from background threads

## Step 2: Setting Up Audio Recording

The app records audio in a background thread to prevent UI freezing:

```python
def record_worker(stop_evt: threading.Event,
                  audio_q: queue.Queue,
                  frames: list[np.ndarray]):
    """Background audio recording - never touches Streamlit UI"""
    def _callback(indata, *_):
        audio_q.put(indata.copy())

    with sd.InputStream(samplerate=16000, channels=1, dtype="int16",
                        callback=_callback):
        while not stop_evt.is_set():
            try:
                frames.append(audio_q.get(timeout=0.1))
            except queue.Empty:
                pass
```

**Why this works:**
- ✅ **Non-blocking**: UI remains responsive during recording
- ✅ **Clean shutdown**: `stop_evt.set()` stops recording instantly
- ✅ **Optimized**: 16kHz mono is perfect for voice recognition

## Step 3: Implementing Thread-Safe UI Updates

The magic happens with `add_script_run_ctx`:

```python
def start_thread(fn, *args, **kwargs):
    """Start a daemon thread that can safely call Streamlit commands"""
    th = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    add_script_run_ctx(th)  # 🔑 This enables st.* calls from background
    th.start()
    return th
```

This allows background threads to update the UI with streaming responses without causing crashes.

## Step 4: Creating the Model Handler Pattern

Each AI model follows the same 4-function pattern:

### Example: Gemini Handler Structure
```python
# chat_handlers/gemini_handler.py

def start_concurrent_streaming(question):
    """Kick off WebUI and/or API streams"""
    if st.session_state.enable_gemini_webui:
        start_thread(handle_concurrent_streaming, question, "webui")
    if st.session_state.enable_gemini_api:
        start_thread(handle_concurrent_streaming, question, "api")

def render_gemini_responses():
    """Display streaming responses in two columns"""
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
    """Background thread that streams tokens to session state"""
    from .gemini_streaming_chat import stream_gemini_response
    
    for chunk in stream_gemini_response(question, stream_type):
        if st.session_state.stop_streaming:
            break
        st.session_state[f"gemini_{stream_type}_streaming_text"] += chunk

def handle_stopped_streaming():
    """Cleanup when user hits stop"""
    if st.session_state.stop_streaming:
        st.session_state.gemini_concurrent_streaming_active = False
        # Reset all flags...
```

## Step 5: Building the Centralized Streaming Loop

Instead of scattered `st.rerun()` calls, one master orchestrator:

```python
def handle_all_streaming():
    """Central hub for all streaming activities"""
    any_streaming = False
    
    # Check each model's streaming status
    for model in ['chatgpt', 'claude', 'grok', 'perplexity', 'gemini']:
        if st.session_state[f"{model}_concurrent_streaming_active"]:
            any_streaming = True
            
            # Check if both streams (WebUI + API) are complete
            webui_done = st.session_state[f"{model}_webui_stream_complete"]
            api_done = st.session_state[f"{model}_api_stream_complete"]
            
            if webui_done and api_done:
                st.session_state[f"{model}_concurrent_streaming_active"] = False
                log_qa_pair(model, ...)  # Save to JSON
                st.success(f"✅ {model.title()} responses completed!")
    
    # Auto-refresh every 200ms if any model is streaming
    if any_streaming:
        time.sleep(0.2)
        st.rerun()
```

## Step 6: Setting Up the User Interface

The UI is organized into logical sections:

### Model Selection Checkboxes
```python
ai_col1, ai_col2, ai_col3, ai_col4, ai_col5 = st.columns(5)

with ai_col1:
    st.markdown("**💬 ChatGPT**")
    chatgpt_col1, chatgpt_col2 = st.columns(2)
    with chatgpt_col1:
        st.session_state.enable_chatgpt_webui = st.checkbox("WebUI", key="chatgpt_webui")
    with chatgpt_col2:
        st.session_state.enable_chatgpt_api = st.checkbox("API", key="chatgpt_api")

# Repeat for Claude, Grok, Perplexity, Gemini...
```

### Auto-Mode Settings
```python
settings_col1, settings_col2, settings_col3 = st.columns(3)

with settings_col1:
    st.session_state.auto_transcribe = st.checkbox("🤖 Auto-transcribe after recording")

with settings_col2:
    st.session_state.auto_chatgpt = st.checkbox("🤖 Auto ChatGPT")

# More auto-mode checkboxes...
```

### Dynamic Tabs for Responses
```python
# Create tabs only for enabled models
tab_names = []
if st.session_state.enable_chatgpt_webui or st.session_state.enable_chatgpt_api:
    tab_names.append("💬 ChatGPT")
if st.session_state.enable_claude_webui or st.session_state.enable_claude_api:
    tab_names.append("🤖 Claude")
# ... continue for all models

if tab_names:
    tabs = st.tabs(tab_names)
    # Render each model's responses in its tab
```

## Step 7: Implementing Session State Management

The app uses 200+ session state variables to track everything:

```python
# Recording state
if "recording" not in st.session_state:
    st.session_state.recording = False
if "last_wav" not in st.session_state:
    st.session_state.last_wav = None

# Per-model streaming states (repeat for each model)
if "gemini_concurrent_streaming_active" not in st.session_state:
    st.session_state.gemini_concurrent_streaming_active = False
if "gemini_webui_streaming_text" not in st.session_state:
    st.session_state.gemini_webui_streaming_text = ""
if "gemini_api_streaming_text" not in st.session_state:
    st.session_state.gemini_api_streaming_text = ""

# Auto-mode flags
if "auto_gemini" not in st.session_state:
    st.session_state.auto_gemini = True

# Logging files
if "gemini_log_file" not in st.session_state:
    session_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.gemini_log_file = os.path.join(
        GEMINI_LOGS_DIR, f"gemini_session_{session_timestamp}.json"
    )
```

## Step 8: Using the Application

### Basic Workflow
1. **Enable Models**: Check WebUI/API boxes for models you want to use
2. **Set Auto-Mode**: Enable auto-transcribe and auto-response for seamless experience
3. **Record**: Press ▶️ Start → speak → press ⏹️ Stop
4. **Compare**: Watch responses stream into separate tabs
5. **Refine**: Edit transcription and press Ctrl+Enter to re-query

### Advanced Features

**Smart Auto-Triggering**: Some models (like Perplexity) start immediately when enabled:
```python
# Perplexity API starts automatically when enabled
if (st.session_state.enable_perplexity_api and 
    st.session_state.transcription and 
    not st.session_state.perplexity_concurrent_streaming_active):
    perplexity_start_concurrent_streaming(question)
```

**Stop All Streaming**: Emergency stop button halts all models:
```python
if st.button("🛑 Stop All Streaming"):
    st.session_state.stop_streaming = True
    # Reset all model streaming flags
    for model in ['chatgpt', 'claude', 'grok', 'perplexity', 'gemini']:
        st.session_state[f"{model}_concurrent_streaming_active"] = False
```

## Step 9: Logging and Conversation History

Each model maintains its own conversation log:

```python
def log_qa_pair(question, webui_answer=None, api_answer=None, model="gemini"):
    """Save Q&A pair to model-specific JSON log"""
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "question": question,
        "webui_response": webui_answer,
        "api_response": api_answer,
        "model": model
    }
    
    log_file = st.session_state[f"{model}_log_file"]
    
    # Append to existing log or create new
    try:
        with open(log_file, 'r') as f:
            logs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logs = []
    
    logs.append(log_entry)
    
    with open(log_file, 'w') as f:
        json.dump(logs, f, indent=2)
```

**Log Structure:**
```
logs/
├── chatgpt/chatgpt_session_20240115_143022.json
├── claude/claude_session_20240115_143022.json
├── grok/grok_session_20240115_143022.json
├── perplexity/perplexity_session_20240115_143022.json
└── gemini/gemini_session_20240115_143022.json
```

## Step 10: Adding a New AI Model

Want to add a sixth model? Follow this pattern:

### 1. Create Handler Module
```python
# chat_handlers/your_model_handler.py
def start_concurrent_streaming(question):
    """Start WebUI and/or API streams"""
    if st.session_state.enable_your_model_webui:
        start_thread(handle_concurrent_streaming, question, "webui")
    if st.session_state.enable_your_model_api:
        start_thread(handle_concurrent_streaming, question, "api")

def render_your_model_responses():
    """Display responses in two columns"""
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🌐 Your Model Web UI**")
        # Display webui streaming text
    with col2:
        st.markdown("**🔌 Your Model API**")
        # Display api streaming text

def handle_concurrent_streaming(question, stream_type):
    """Background streaming logic"""
    # Your streaming implementation here
    pass

def handle_stopped_streaming():
    """Cleanup on stop"""
    # Reset flags when stopped
    pass
```

### 2. Add Session State Variables
```python
# Add to main app initialization
if "your_model_concurrent_streaming_active" not in st.session_state:
    st.session_state.your_model_concurrent_streaming_active = False
if "your_model_webui_streaming_text" not in st.session_state:
    st.session_state.your_model_webui_streaming_text = ""
# ... add all necessary state variables
```

### 3. Wire UI Components
```python
# Add to model selection section
with ai_col6:  # Add a 6th column
    st.markdown("**🆕 Your Model**")
    your_model_col1, your_model_col2 = st.columns(2)
    with your_model_col1:
        st.session_state.enable_your_model_webui = st.checkbox("WebUI")
    with your_model_col2:
        st.session_state.enable_your_model_api = st.checkbox("API")

# Add to tabs
if st.session_state.enable_your_model_webui or st.session_state.enable_your_model_api:
    tab_names.append("🆕 Your Model")

# Add to streaming handler
if st.session_state.your_model_concurrent_streaming_active:
    any_streaming = True
    # Check completion logic...
```

## Performance Optimization Tips

**🚀 Batch Token Updates**: Update UI every ~20 tokens instead of per-token:
```python
token_buffer = ""
token_count = 0

for chunk in stream_response():
    token_buffer += chunk
    token_count += 1
    
    if token_count >= 20:  # Batch update
        st.session_state.streaming_text += token_buffer
        token_buffer = ""
        token_count = 0
```

**🚀 Selective Model Enabling**: Only enable models you're actively comparing to reduce CPU/memory usage.

**🚀 Local Whisper**: For heavy transcription workloads:
```bash
pip install openai-whisper
# Use local whisper-tiny model instead of API
```

**🚀 Chrome Debugging**: WebUI handlers assume Chrome with `--remote-debugging-port=9222` for free response scraping.

## Troubleshooting Common Issues

### Threading Errors
**Problem**: `RuntimeError: Cannot call st.* from a thread`  
**Solution**: Ensure `add_script_run_ctx(thread)` is called before starting threads.

### UI Not Updating
**Problem**: Streaming text doesn't appear  
**Solution**: Check that `st.rerun()` is called in the central streaming loop.

### Audio Recording Fails
**Problem**: No audio captured  
**Solution**: Check microphone permissions and `sounddevice` installation.

### Model Not Responding
**Problem**: Specific model doesn't stream  
**Solution**: Verify API keys in `.env` and check handler implementation.

## Advanced Customization

### Custom CSS Styling
The app includes extensive CSS for proper text wrapping and tab styling:
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

### Environment Variables
```bash
# .env file
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_claude_key
XAI_API_KEY=your_grok_key
PERPLEXITY_API_KEY=your_perplexity_key
GOOGLE_API_KEY=your_gemini_key
```

## What's Next?

**🔄 Streaming Audio Upload**: Direct S3 upload for long conversations  
**🖼️ Multimodal Support**: Screenshot-to-prompt for visual questions  
**🔬 Response Scoring**: A/B testing widget with CSV export  
**📈 Analytics Dashboard**: Latency and token-per-second metrics  
**🎯 Local LLM Support**: Ollama, LM Studio integration  
**🔊 Text-to-Speech**: Hear responses back with voice synthesis  

## Complete File Structure

```
📁 ui_interview_copilot/
├── gemini_model_chat_app.py          # Main Streamlit app
├── .env                              # API keys (create from template)
├── requirements.txt                  # Python dependencies
├── 📁 chat_handlers/
│   ├── chatgpt_handler.py           # ChatGPT WebUI + API
│   ├── claude_handler.py            # Claude WebUI + API
│   ├── grok_handler.py              # Grok WebUI + API
│   ├── perplexity_handler.py        # Perplexity WebUI + API
│   └── gemini_handler.py            # Gemini WebUI + API
├── 📁 include/
│   └── transcribe.py                # Whisper transcription wrapper
├── 📁 logs/                         # Conversation logs (auto-created)
│   ├── chatgpt/
│   ├── claude/
│   ├── grok/
│   ├── perplexity/
│   └── gemini/
└── 📁 recordings/                   # Audio files (auto-created)
```

## Final Thoughts

This step-by-step guide shows you how to build a production-grade voice chat application that simultaneously queries five major AI models. The modular architecture makes it easy to add new models, while the thread-safe design ensures smooth performance.

Whether you're researching AI model differences, building a comparison tool, or just curious about how different models respond to the same question, this single-file solution provides a solid foundation that's both powerful and extensible.

**Ready to start?** Copy the code, configure your API keys, and begin exploring the fascinating world of multi-model AI conversations!

---

**Tags:** #streamlit #voice #ai #chatgpt #claude #grok #perplexity #gemini #python #threading #concurrent #whisper #comparison #tutorial

Happy coding & may your AI conversations be insightful! 🚀
