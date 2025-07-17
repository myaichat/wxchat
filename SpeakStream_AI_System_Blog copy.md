# SpeakStream AI: A Voice-Enabled ChatGPT Streaming System

## Overview

SpeakStream AI is a sophisticated voice-to-text-to-ChatGPT system that enables users to record audio, automatically transcribe it, and get streaming responses from ChatGPT through multiple channels. The system consists of three main components working together to provide a seamless voice-driven AI interaction experience.

## System Architecture

The system is built with a three-tier architecture:

1. **Frontend**: Streamlit web application (`chat_app.py`)
2. **Backend Proxy**: FastAPI server (`streaming_server.py`) 
3. **WebSocket Client**: Chrome DevTools integration (`streaming_chat.py`)

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit     │───▶│   FastAPI        │───▶│  Chrome DevTools│
│   Frontend      │    │   Proxy Server   │    │  WebSocket      │
│   (chat_app.py) │    │(streaming_server)│    │(streaming_chat) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                                               │
         │              Direct OpenAI API               │
         └──────────────────────────────────────────────┘
```

## Key Features

### 🎙️ Voice Recording & Transcription
- **Real-time audio recording** using `sounddevice` library
- **Thread-safe recording** with proper session state management
- **Automatic transcription** using OpenAI Whisper API
- **Manual transcription editing** with form-based input
- **Auto-transcribe toggle** for hands-free operation

### 🚀 Dual Streaming Responses
The system provides **concurrent streaming** from two sources:
1. **Web UI Streaming**: Via Chrome DevTools WebSocket connection
2. **API Streaming**: Direct OpenAI API calls

Both streams run simultaneously, allowing users to compare responses in real-time.

### 📝 Smart Streaming Display
- **Incremental text updates** with cursor indicator (▌)
- **Smart breakpoint detection** for natural text flow
- **Unicode handling** for special characters and emojis
- **Stop streaming** functionality with user control

### 💾 Comprehensive Logging
- **Session-based logging** with timestamped JSON files
- **Question-answer pair tracking** with model information
- **Separate logs** for server and client interactions
- **UTF-8 encoding support** for international characters

## Technical Implementation

### Frontend (chat_app.py)

The Streamlit frontend is the user-facing component with several sophisticated features:

#### Session State Management
```python
# Key session state variables
if "recording" not in st.session_state:
    st.session_state.recording = False
if "transcription" not in st.session_state:
    st.session_state.transcription = None
if "concurrent_streaming_active" not in st.session_state:
    st.session_state.concurrent_streaming_active = False
```

#### Thread-Safe Audio Recording
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

#### Concurrent Streaming Implementation
The system implements sophisticated concurrent streaming with separate worker threads:

```python
def start_concurrent_streaming(question):
    """Start both Web UI and API streaming concurrently"""
    st.session_state.concurrent_streaming_active = True
    st.session_state.webui_streaming_text = ""
    st.session_state.api_streaming_text = ""
    
    # Start both streaming threads
    start_thread(webui_streaming_worker, question)
    start_thread(api_streaming_worker, question)
```

### Backend Proxy (streaming_server.py)

The FastAPI server acts as a bridge between the Streamlit frontend and the Chrome DevTools WebSocket:

#### Server-Sent Events Streaming
```python
async def event_stream(message: str, timeout: int) -> AsyncGenerator[bytes, None]:
    """Server‑Sent‑Events wrapper around send_message_with_streaming() with logging."""
    complete_answer = ""
    
    async for chunk in send_message_with_streaming(message, timeout):
        yield (json.dumps(chunk) + "\n").encode("utf-8")
        
        if chunk.get("status") == "complete":
            complete_answer = chunk.get("content", "")
            save_chat_log(message, complete_answer)
```

#### Automatic Logging
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

### WebSocket Client (streaming_chat.py)

The most complex component handles Chrome DevTools WebSocket communication:

#### JavaScript Injection for Response Monitoring
The system injects sophisticated JavaScript code into the ChatGPT web page:

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

#### Streaming Response Generator
```python
async def send_message_with_streaming(message, timeout=120):
    """Generator that yields streaming responses as they arrive"""
    async with websockets.connect(ws_url) as websocket:
        # Set up observer and send message
        await websocket.send(json.dumps({
            "id": 3,
            "method": "Runtime.evaluate",
            "params": {"expression": observer_js, "returnByValue": True}
        }))
        
        # Process streaming responses
        while not response_complete:
            message = await websocket.recv()
            data = json.loads(message)
            
            if data.get("method") == "Runtime.consoleAPICalled":
                console_message = args[0].get("value", "")
                
                if console_message.startswith("RESPONSE_UPDATE:"):
                    content = console_message.replace("RESPONSE_UPDATE:", "")
                    yield {"status": "streaming", "content": content}
                elif console_message.startswith("RESPONSE_COMPLETE:"):
                    content = console_message.replace("RESPONSE_COMPLETE:", "")
                    yield {"status": "complete", "content": content}
```

## Smart Streaming Features

### Intelligent Text Chunking
The system implements smart breakpoint detection for natural text flow:

```python
safe_patterns = [
    '\n\n',  # Paragraph breaks
    '\n- ',  # List items  
    '\n## ', # Headers
    '. ',    # Sentence endings
    '! ',    # Exclamations
    '? ',    # Questions
    ', ',    # Commas
    '**.',   # Bold endings with period
    '`.',    # Code endings with period
    '```\n', # Code block endings
]
```

### Response Completion Detection
Multiple methods ensure accurate completion detection:
- Copy button presence detection
- Natural text ending patterns
- Stability timeout (content unchanged for specified duration)
- Maximum timeout protection

## Configuration & Environment

### Required Environment Variables
```bash
OPENAI_API_KEY=your_openai_api_key_here
CHATGPT_DEVTOOLS_WS=ws://localhost:9222/devtools/page/[PAGE_ID]
```

### Dependencies
- **Streamlit**: Web interface framework
- **FastAPI**: Backend API server
- **WebSockets**: Chrome DevTools communication
- **SoundDevice**: Audio recording
- **OpenAI**: API integration and Whisper transcription
- **Requests**: HTTP client for streaming

## Usage Workflow

1. **Start the system**:
   ```bash
   # Terminal 1: Start the FastAPI proxy server
   python streaming_server.py
   
   # Terminal 2: Start the Streamlit frontend
   streamlit run chat_app.py
   ```

2. **Record audio**: Click "▶️ Start" to begin recording, "⏹️ Stop" to finish

3. **Auto-transcription**: If enabled, transcription happens automatically

4. **Get responses**: 
   - Manual: Click "💬 Get ChatGPT Response" 
   - Auto: Responses generate automatically if auto-ChatGPT is enabled

5. **View streaming**: Watch both Web UI and API responses stream in real-time

6. **Stop if needed**: Use "🛑 Stop Streaming" to halt response generation

## Advanced Features

### Model Selection
Support for multiple OpenAI models:
- GPT-4, GPT-4-turbo, GPT-4o, GPT-4o-mini
- GPT-3.5-turbo, GPT-3.5-turbo-16k

### Conversation History
- Maintains conversation context across interactions
- Proper role-based message formatting
- Session persistence during app runtime

### Error Handling
- Comprehensive exception handling for all components
- Graceful degradation when services are unavailable
- User-friendly error messages and recovery options

### Performance Optimizations
- Thread-safe operations with proper context management
- Efficient audio buffering and processing
- Smart UI refresh rates during streaming
- Memory-conscious session state management

## Logging and Monitoring

The system provides comprehensive logging:

### Session Logs
```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "question": "What is machine learning?",
  "answer": "Machine learning is a subset of artificial intelligence...",
  "model": "gpt-4o"
}
```

### Server Logs
- Individual timestamped files for each interaction
- UTF-8 encoding for international character support
- Structured JSON format for easy parsing

## Security Considerations

- Environment variable protection for API keys
- Local WebSocket connections only
- No persistent storage of sensitive data
- Session-based temporary file management

## Future Enhancements

Potential improvements for the system:
- **Multi-language support** for transcription
- **Voice synthesis** for audio responses
- **Custom model fine-tuning** integration
- **Real-time collaboration** features
- **Mobile app** companion
- **Cloud deployment** options

## Conclusion

SpeakStream AI represents a sophisticated integration of voice recognition, real-time streaming, and AI interaction technologies. The system's architecture demonstrates advanced concepts in:

- **Concurrent programming** with thread-safe operations
- **Real-time streaming** with multiple data sources
- **WebSocket communication** with browser automation
- **Modern web frameworks** integration
- **Audio processing** and transcription

The modular design allows for easy extension and customization, making it suitable for various voice-driven AI applications beyond ChatGPT integration.

---

*This system showcases the power of combining multiple technologies to create seamless voice-to-AI interactions, representing the future of human-computer interface design.*
