# simple_chat_app.py  –  thread‑safe Streamlit mic recorder with direct streaming_chat calls
import streamlit as st

# Configure page layout to be wide
st.set_page_config(
    page_title="SpeakStream AI",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for tab-like headers with much smaller styling and fix transparency issues
st.markdown("""
<style>
.box-header {
    font-size: 26px;
    font-weight: 550;
    color: #4f46e5; /* Indigo-600 */
    margin-bottom: 6px;
    margin-left: 0px;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Fix tab transparency and duplication issues */
.stTabs [data-baseweb="tab-list"] {
    background-color: transparent !important;
}

.stTabs [data-baseweb="tab"] {
    background-color: transparent !important;
    opacity: 1 !important;
}

.stTabs [data-baseweb="tab-panel"] {
    background-color: transparent !important;
    opacity: 1 !important;
    padding-top: 1rem;
}

/* Ensure proper z-index for tabs */
.stTabs {
    z-index: 1 !important;
}

/* Fix any potential overlay issues */
.stTabs > div {
    background-color: transparent !important;
}

/* Fix text wrapping and overflow issues in columns */
.stColumn > div {
    word-wrap: break-word !important;
    overflow-wrap: break-word !important;
    max-width: 100% !important;
}

/* Ensure markdown content wraps properly and maintains formatting */
.stMarkdown {
    word-wrap: break-word !important;
    overflow-wrap: break-word !important;
    max-width: 100% !important;
    overflow-x: hidden !important;
    line-height: 1.6 !important;
    font-size: 14px !important;
}

/* Preserve markdown structure while allowing wrapping */
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
    margin-top: 1.5em !important;
    margin-bottom: 0.5em !important;
    line-height: 1.3 !important;
    word-wrap: break-word !important;
}

.stMarkdown p {
    margin-bottom: 1em !important;
    word-wrap: break-word !important;
    overflow-wrap: break-word !important;
}

.stMarkdown ul, .stMarkdown ol {
    margin-bottom: 1em !important;
    padding-left: 1.5em !important;
}

.stMarkdown li {
    margin-bottom: 0.5em !important;
    word-wrap: break-word !important;
    overflow-wrap: break-word !important;
}

.stMarkdown table {
    width: 100% !important;
    border-collapse: collapse !important;
    margin-bottom: 1em !important;
    font-size: 12px !important;
}

.stMarkdown th, .stMarkdown td {
    border: 1px solid #ddd !important;
    padding: 8px !important;
    text-align: left !important;
    word-wrap: break-word !important;
    overflow-wrap: break-word !important;
}

.stMarkdown th {
    background-color: #f5f5f5 !important;
    font-weight: bold !important;
}

/* Fix column content overflow */
[data-testid="column"] {
    overflow-x: hidden !important;
    padding-right: 10px !important;
}

[data-testid="column"] > div {
    word-wrap: break-word !important;
    overflow-wrap: break-word !important;
    max-width: 100% !important;
}

/* Ensure code blocks wrap properly */
.stMarkdown pre, .stMarkdown code {
    word-wrap: break-word !important;
    overflow-wrap: break-word !important;
    white-space: pre-wrap !important;
    max-width: 100% !important;
}

/* Fix blockquotes */
.stMarkdown blockquote {
    border-left: 4px solid #ddd !important;
    padding-left: 1em !important;
    margin-left: 0 !important;
    margin-bottom: 1em !important;
    font-style: italic !important;
}
</style>
""", unsafe_allow_html=True)

import sounddevice as sd
import numpy as np
import wave, os, io, queue, threading, datetime
import json
import asyncio
from include.transcribe import Transcribe
from pathlib import Path
from dotenv import load_dotenv
from streamlit.runtime.scriptrunner import add_script_run_ctx

# Import ChatGPT handler module
from chat_handlers.chatgpt_handler import (
    start_concurrent_streaming as chatgpt_start_concurrent_streaming, 
    render_chatgpt_responses, 
    handle_concurrent_streaming as chatgpt_handle_concurrent_streaming, 
    handle_stopped_streaming as chatgpt_handle_stopped_streaming
)

# Import Claude handler module
from chat_handlers.claude_handler import (
    start_concurrent_streaming as claude_start_concurrent_streaming,
    render_claude_responses,
    handle_concurrent_streaming as claude_handle_concurrent_streaming,
    handle_stopped_streaming as claude_handle_stopped_streaming
)

# Import Grok handler module
from chat_handlers.grok_handler import (
    start_concurrent_streaming as grok_start_concurrent_streaming,
    render_grok_responses,
    handle_concurrent_streaming as grok_handle_concurrent_streaming,
    handle_stopped_streaming as grok_handle_stopped_streaming
)

# Import Perplexity handler module
from chat_handlers.perplexity_handler import (
    start_concurrent_streaming as perplexity_start_concurrent_streaming,
    render_perplexity_responses,
    handle_concurrent_streaming as perplexity_handle_concurrent_streaming,
    handle_stopped_streaming as perplexity_handle_stopped_streaming
)

# Import Gemini handler module
from chat_handlers.gemini_handler import (
    start_concurrent_streaming as gemini_start_concurrent_streaming,
    render_gemini_responses,
    handle_concurrent_streaming as gemini_handle_concurrent_streaming,
    handle_stopped_streaming as gemini_handle_stopped_streaming
)

# Load environment variables from .env file
load_dotenv(dotenv_path=Path(".") / ".env", override=True)

RATE, CH = 16_000, 1
OUT_DIR  = "recordings"
os.makedirs(OUT_DIR, exist_ok=True)

TIMEOUT_SEC = 60

# Logging configuration
LOGS_DIR = "logs"
CHATGPT_LOGS_DIR = os.path.join(LOGS_DIR, "chatgpt")
CLAUDE_LOGS_DIR = os.path.join(LOGS_DIR, "claude")
GROK_LOGS_DIR = os.path.join(LOGS_DIR, "grok")
PERPLEXITY_LOGS_DIR = os.path.join(LOGS_DIR, "perplexity")
GEMINI_LOGS_DIR = os.path.join(LOGS_DIR, "gemini")
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(CHATGPT_LOGS_DIR, exist_ok=True)
os.makedirs(CLAUDE_LOGS_DIR, exist_ok=True)
os.makedirs(GROK_LOGS_DIR, exist_ok=True)
os.makedirs(PERPLEXITY_LOGS_DIR, exist_ok=True)
os.makedirs(GEMINI_LOGS_DIR, exist_ok=True)

# ───────────────────── session defaults ─────────────────────
if "recording" not in st.session_state:
    st.session_state.recording = False
if "last_wav" not in st.session_state:
    st.session_state.last_wav = None        # path of most recent save
if "transcription" not in st.session_state:
    st.session_state.transcription = None   # transcription text
if "transcribing" not in st.session_state:
    st.session_state.transcribing = False   # transcription in progress
if "transcriber" not in st.session_state:
    st.session_state.transcriber = None     # transcriber instance
if "auto_transcribe" not in st.session_state:
    st.session_state.auto_transcribe = True # auto transcribe enabled by default
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "api_conversation_history" not in st.session_state:
    st.session_state.api_conversation_history = []
if "chatgpt_response" not in st.session_state:
    st.session_state.chatgpt_response = None
if "generating_response" not in st.session_state:
    st.session_state.generating_response = False
if "selected_model" not in st.session_state:
    st.session_state.selected_model = "gpt-4o"  # default model
if "auto_chatgpt" not in st.session_state:
    st.session_state.auto_chatgpt = True  # auto ChatGPT enabled by default
if "auto_claude" not in st.session_state:
    st.session_state.auto_claude = True  # auto Claude enabled by default
if "stop_streaming" not in st.session_state:
    st.session_state.stop_streaming = False  # flag to stop streaming
if "manual_transcription" not in st.session_state:
    st.session_state.manual_transcription = None  # store manual transcription for processing
if "chatgpt_log_file" not in st.session_state:
    # Create a unique ChatGPT log file for this session
    session_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.chatgpt_log_file = os.path.join(CHATGPT_LOGS_DIR, f"chatgpt_session_{session_timestamp}.json")
if "claude_log_file" not in st.session_state:
    # Create a unique Claude log file for this session
    session_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.claude_log_file = os.path.join(CLAUDE_LOGS_DIR, f"claude_session_{session_timestamp}.json")
# Keep the old session_log_file for backward compatibility (will be used by ChatGPT by default)
if "session_log_file" not in st.session_state:
    st.session_state.session_log_file = st.session_state.chatgpt_log_file
if "api_response" not in st.session_state:
    st.session_state.api_response = None  # store API response separately
if "generating_api_response" not in st.session_state:
    st.session_state.generating_api_response = False  # flag for API response generation
if "webui_streaming_text" not in st.session_state:
    st.session_state.webui_streaming_text = ""
if "api_streaming_text" not in st.session_state:
    st.session_state.api_streaming_text = ""
if "webui_stream_complete" not in st.session_state:
    st.session_state.webui_stream_complete = False
if "api_stream_complete" not in st.session_state:
    st.session_state.api_stream_complete = False
if "concurrent_streaming_active" not in st.session_state:
    st.session_state.concurrent_streaming_active = False
if "pending_log_question" not in st.session_state:
    st.session_state.pending_log_question = None  # store question for logging when both responses complete
if "pending_log_webui_question" not in st.session_state:
    st.session_state.pending_log_webui_question = None  # store Web UI question for logging
if "pending_log_api_question" not in st.session_state:
    st.session_state.pending_log_api_question = None  # store API question for logging

# Claude-specific session state variables
if "claude_conversation_history" not in st.session_state:
    st.session_state.claude_conversation_history = []
if "claude_api_conversation_history" not in st.session_state:
    st.session_state.claude_api_conversation_history = []
if "claude_response" not in st.session_state:
    st.session_state.claude_response = None
if "claude_api_response" not in st.session_state:
    st.session_state.claude_api_response = None
if "claude_webui_streaming_text" not in st.session_state:
    st.session_state.claude_webui_streaming_text = ""
if "claude_api_streaming_text" not in st.session_state:
    st.session_state.claude_api_streaming_text = ""
if "claude_webui_stream_complete" not in st.session_state:
    st.session_state.claude_webui_stream_complete = False
if "claude_api_stream_complete" not in st.session_state:
    st.session_state.claude_api_stream_complete = False
if "claude_concurrent_streaming_active" not in st.session_state:
    st.session_state.claude_concurrent_streaming_active = False
if "claude_generating_response" not in st.session_state:
    st.session_state.claude_generating_response = False
if "claude_generating_api_response" not in st.session_state:
    st.session_state.claude_generating_api_response = False
if "claude_pending_log_question" not in st.session_state:
    st.session_state.claude_pending_log_question = None
if "claude_pending_log_webui_question" not in st.session_state:
    st.session_state.claude_pending_log_webui_question = None
if "claude_pending_log_api_question" not in st.session_state:
    st.session_state.claude_pending_log_api_question = None

# Grok-specific session state variables
if "grok_log_file" not in st.session_state:
    # Create a unique Grok log file for this session
    session_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.grok_log_file = os.path.join(GROK_LOGS_DIR, f"grok_session_{session_timestamp}.json")
if "auto_grok" not in st.session_state:
    st.session_state.auto_grok = True  # auto Grok enabled by default
if "grok_conversation_history" not in st.session_state:
    st.session_state.grok_conversation_history = []
if "grok_api_conversation_history" not in st.session_state:
    st.session_state.grok_api_conversation_history = []
if "grok_response" not in st.session_state:
    st.session_state.grok_response = None
if "grok_api_response" not in st.session_state:
    st.session_state.grok_api_response = None
if "grok_webui_streaming_text" not in st.session_state:
    st.session_state.grok_webui_streaming_text = ""
if "grok_api_streaming_text" not in st.session_state:
    st.session_state.grok_api_streaming_text = ""
if "grok_webui_stream_complete" not in st.session_state:
    st.session_state.grok_webui_stream_complete = False
if "grok_api_stream_complete" not in st.session_state:
    st.session_state.grok_api_stream_complete = False
if "grok_concurrent_streaming_active" not in st.session_state:
    st.session_state.grok_concurrent_streaming_active = False
if "grok_generating_response" not in st.session_state:
    st.session_state.grok_generating_response = False
if "grok_generating_api_response" not in st.session_state:
    st.session_state.grok_generating_api_response = False
if "grok_pending_log_question" not in st.session_state:
    st.session_state.grok_pending_log_question = None
if "grok_pending_log_webui_question" not in st.session_state:
    st.session_state.grok_pending_log_webui_question = None
if "grok_pending_log_api_question" not in st.session_state:
    st.session_state.grok_pending_log_api_question = None

# Perplexity-specific session state variables
if "perplexity_log_file" not in st.session_state:
    # Create a unique Perplexity log file for this session
    session_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.perplexity_log_file = os.path.join(PERPLEXITY_LOGS_DIR, f"perplexity_session_{session_timestamp}.json")
if "auto_perplexity" not in st.session_state:
    st.session_state.auto_perplexity = True  # auto Perplexity enabled by default
if "perplexity_conversation_history" not in st.session_state:
    st.session_state.perplexity_conversation_history = []
if "perplexity_api_conversation_history" not in st.session_state:
    st.session_state.perplexity_api_conversation_history = []
if "perplexity_response" not in st.session_state:
    st.session_state.perplexity_response = None
if "perplexity_api_response" not in st.session_state:
    st.session_state.perplexity_api_response = None
if "perplexity_webui_streaming_text" not in st.session_state:
    st.session_state.perplexity_webui_streaming_text = ""
if "perplexity_api_streaming_text" not in st.session_state:
    st.session_state.perplexity_api_streaming_text = ""
if "perplexity_webui_stream_complete" not in st.session_state:
    st.session_state.perplexity_webui_stream_complete = False
if "perplexity_api_stream_complete" not in st.session_state:
    st.session_state.perplexity_api_stream_complete = False
if "perplexity_concurrent_streaming_active" not in st.session_state:
    st.session_state.perplexity_concurrent_streaming_active = False
if "perplexity_generating_response" not in st.session_state:
    st.session_state.perplexity_generating_response = False
if "perplexity_generating_api_response" not in st.session_state:
    st.session_state.perplexity_generating_api_response = False
if "perplexity_pending_log_question" not in st.session_state:
    st.session_state.perplexity_pending_log_question = None
if "perplexity_pending_log_webui_question" not in st.session_state:
    st.session_state.perplexity_pending_log_webui_question = None
if "perplexity_pending_log_api_question" not in st.session_state:
    st.session_state.perplexity_pending_log_api_question = None
# Additional Perplexity session state variables that were missing
if "show_perplexity_history" not in st.session_state:
    st.session_state.show_perplexity_history = False
if "perplexity_processed_transcription" not in st.session_state:
    st.session_state.perplexity_processed_transcription = None  # Track which transcription was last processed

# Gemini-specific session state variables
if "gemini_log_file" not in st.session_state:
    # Create a unique Gemini log file for this session
    session_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.gemini_log_file = os.path.join(GEMINI_LOGS_DIR, f"gemini_session_{session_timestamp}.json")
if "auto_gemini" not in st.session_state:
    st.session_state.auto_gemini = True  # auto Gemini enabled by default
if "gemini_conversation_history" not in st.session_state:
    st.session_state.gemini_conversation_history = []
if "gemini_api_conversation_history" not in st.session_state:
    st.session_state.gemini_api_conversation_history = []
if "gemini_response" not in st.session_state:
    st.session_state.gemini_response = None
if "gemini_api_response" not in st.session_state:
    st.session_state.gemini_api_response = None
if "gemini_webui_streaming_text" not in st.session_state:
    st.session_state.gemini_webui_streaming_text = ""
if "gemini_api_streaming_text" not in st.session_state:
    st.session_state.gemini_api_streaming_text = ""
if "gemini_webui_stream_complete" not in st.session_state:
    st.session_state.gemini_webui_stream_complete = False
if "gemini_api_stream_complete" not in st.session_state:
    st.session_state.gemini_api_stream_complete = False
if "gemini_concurrent_streaming_active" not in st.session_state:
    st.session_state.gemini_concurrent_streaming_active = False
if "gemini_generating_response" not in st.session_state:
    st.session_state.gemini_generating_response = False
if "gemini_generating_api_response" not in st.session_state:
    st.session_state.gemini_generating_api_response = False
if "gemini_pending_log_question" not in st.session_state:
    st.session_state.gemini_pending_log_question = None
if "gemini_pending_log_webui_question" not in st.session_state:
    st.session_state.gemini_pending_log_webui_question = None
if "gemini_pending_log_api_question" not in st.session_state:
    st.session_state.gemini_pending_log_api_question = None
if "show_gemini_history" not in st.session_state:
    st.session_state.show_gemini_history = False
if "gemini_processed_transcription" not in st.session_state:
    st.session_state.gemini_processed_transcription = None  # Track which transcription was last processed

# ───────────────────── helper functions ─────────────────────
def start_thread(fn, *args, **kwargs):
    """Utility – start a daemon thread that can call Streamlit commands."""
    th = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    add_script_run_ctx(th)          # <- critical line
    th.start()
    return th

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

def save_wav(frames) -> str | None:
    if not frames:
        return None
    pcm = np.concatenate(frames).tobytes()

    ts   = datetime.datetime.now().strftime("%Y%m%d‑%H%M%S")
    path = os.path.join(OUT_DIR, f"{ts}.wav")
    with wave.open(path, "wb") as wf:
        wf.setnchannels(CH)
        wf.setsampwidth(2)     # int16
        wf.setframerate(RATE)
        wf.writeframes(pcm)
    return path

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

# 🆕 Always return the text the user sees/edits
def current_transcription() -> str | None:
    return st.session_state.get("transcription_display",
                                st.session_state.transcription)


# ───────────────────────── UI ───────────────────────────────
# Title and Model Selection in same row
title_col, model_col = st.columns([4, 1])

with title_col:
    st.title("🎙️ SpeakStream AI")

with model_col:
    # Model selection dropdown next to title
    available_models = [
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k"
    ]
    
    st.session_state.selected_model = st.selectbox(
        "Model:",
        available_models,
        index=available_models.index(st.session_state.selected_model)
    )

# ---------- AI Model Selection ----------
if "enable_chatgpt_webui" not in st.session_state:
    st.session_state.enable_chatgpt_webui = False
if "enable_chatgpt_api" not in st.session_state:
    st.session_state.enable_chatgpt_api = False
if "enable_claude_webui" not in st.session_state:
    st.session_state.enable_claude_webui = False
if "enable_claude_api" not in st.session_state:
    st.session_state.enable_claude_api = False
if "enable_grok_webui" not in st.session_state:
    st.session_state.enable_grok_webui = False
if "enable_grok_api" not in st.session_state:
    st.session_state.enable_grok_api = False
if "enable_perplexity_webui" not in st.session_state:
    st.session_state.enable_perplexity_webui = False
if "enable_perplexity_api" not in st.session_state:
    st.session_state.enable_perplexity_api = False
if "enable_gemini_webui" not in st.session_state:
    st.session_state.enable_gemini_webui = True
if "enable_gemini_api" not in st.session_state:
    st.session_state.enable_gemini_api = True

ai_col1, ai_col2, ai_col3, ai_col4, ai_col5 = st.columns(5)

with ai_col1:
    st.markdown("**💬 ChatGPT**")
    chatgpt_col1, chatgpt_col2 = st.columns(2)
    with chatgpt_col1:
        st.session_state.enable_chatgpt_webui = st.checkbox("WebUI", 
                                                           value=st.session_state.enable_chatgpt_webui,
                                                           key="chatgpt_webui")
    with chatgpt_col2:
        st.session_state.enable_chatgpt_api = st.checkbox("API", 
                                                         value=st.session_state.enable_chatgpt_api,
                                                         key="chatgpt_api")

with ai_col2:
    st.markdown("**🤖 Claude**")
    claude_col1, claude_col2 = st.columns(2)
    with claude_col1:
        st.session_state.enable_claude_webui = st.checkbox("WebUI", 
                                                          value=st.session_state.enable_claude_webui,
                                                          key="claude_webui")
    with claude_col2:
        st.session_state.enable_claude_api = st.checkbox("API", 
                                                        value=st.session_state.enable_claude_api,
                                                        key="claude_api")

with ai_col3:
    st.markdown("**🚀 Grok**")
    grok_col1, grok_col2 = st.columns(2)
    with grok_col1:
        st.session_state.enable_grok_webui = st.checkbox("Web UI", 
                                                        value=st.session_state.enable_grok_webui,
                                                        key="grok_webui")
    with grok_col2:
        st.session_state.enable_grok_api = st.checkbox("API", 
                                                      value=st.session_state.enable_grok_api,
                                                      key="grok_api")

with ai_col4:
    st.markdown("**🔍 Perplexity**")
    perplexity_col1, perplexity_col2 = st.columns(2)
    with perplexity_col1:
        st.session_state.enable_perplexity_webui = st.checkbox("Web UI", 
                                                              value=st.session_state.enable_perplexity_webui,
                                                              key="perplexity_webui")
    with perplexity_col2:
        # Store previous API state to detect changes
        prev_api_state = st.session_state.get("prev_perplexity_api_state", False)
        st.session_state.enable_perplexity_api = st.checkbox("API", 
                                                            value=st.session_state.enable_perplexity_api,
                                                            key="perplexity_api")
        
        # If API was just enabled and we have a transcription, start streaming immediately
        if (st.session_state.enable_perplexity_api and 
            not prev_api_state and 
            st.session_state.transcription and 
            not st.session_state.recording and
            not st.session_state.perplexity_concurrent_streaming_active):
            question = current_transcription()
            if question:
                perplexity_start_concurrent_streaming(question)
                st.rerun()
        
        # Update previous state
        st.session_state.prev_perplexity_api_state = st.session_state.enable_perplexity_api

with ai_col5:
    st.markdown("**💎 Gemini**")
    gemini_col1, gemini_col2 = st.columns(2)
    with gemini_col1:
        st.session_state.enable_gemini_webui = st.checkbox("Web UI", 
                                                          value=st.session_state.enable_gemini_webui,
                                                          key="gemini_webui")
    with gemini_col2:
        st.session_state.enable_gemini_api = st.checkbox("API", 
                                                        value=st.session_state.enable_gemini_api,
                                                        key="gemini_api")

# ---------- Settings ----------
settings_col1, settings_col2, settings_col3, settings_col4, settings_col5, settings_col6 = st.columns(6)

with settings_col1:
    st.session_state.auto_transcribe = st.checkbox("🤖 Auto-transcribe after recording", 
                                                   value=st.session_state.auto_transcribe)

with settings_col2:
    st.session_state.auto_chatgpt = st.checkbox("🤖 Auto ChatGPT", 
                                               value=st.session_state.auto_chatgpt)

with settings_col3:
    st.session_state.auto_claude = st.checkbox("🤖 Auto Claude", 
                                              value=st.session_state.auto_claude)

with settings_col4:
    st.session_state.auto_grok = st.checkbox("🤖 Auto Grok", 
                                            value=st.session_state.auto_grok)

with settings_col5:
    st.session_state.auto_perplexity = st.checkbox("🤖 Auto Perplexity", 
                                                  value=st.session_state.auto_perplexity)

with settings_col6:
    st.session_state.auto_gemini = st.checkbox("🤖 Auto Gemini", 
                                              value=st.session_state.auto_gemini)

# ────────── Start / Stop toggle (replaces the old two‑button section) ──────────
label = "▶️ Start" if not st.session_state.recording else "⏹️ Stop"

if st.button(label, key="rec_toggle"):
    if not st.session_state.recording:          # ───── START branch ─────
        st.session_state.recording   = True
        st.session_state.transcription       = None
        st.session_state.transcribing        = False
        st.session_state.chatgpt_response    = None
        st.session_state.generating_response = False
        st.session_state.api_response        = None  # Clear API response for new recording
        st.session_state.generating_api_response = False  # Clear API generation flag
        
        # Clear Claude responses for new recording
        st.session_state.claude_response = None
        st.session_state.claude_api_response = None
        st.session_state.claude_webui_streaming_text = ""
        st.session_state.claude_api_streaming_text = ""
        st.session_state.claude_webui_stream_complete = False
        st.session_state.claude_api_stream_complete = False
        st.session_state.claude_concurrent_streaming_active = False
        st.session_state.claude_generating_response = False
        st.session_state.claude_generating_api_response = False

        # Clear Grok responses for new recording
        st.session_state.grok_response = None
        st.session_state.grok_api_response = None
        st.session_state.grok_webui_streaming_text = ""
        st.session_state.grok_api_streaming_text = ""
        st.session_state.grok_webui_stream_complete = False
        st.session_state.grok_api_stream_complete = False
        st.session_state.grok_concurrent_streaming_active = False
        st.session_state.grok_generating_response = False
        st.session_state.grok_generating_api_response = False

        # Clear Perplexity responses for new recording
        st.session_state.perplexity_response = None
        st.session_state.perplexity_api_response = None
        st.session_state.perplexity_webui_streaming_text = ""
        st.session_state.perplexity_api_streaming_text = ""
        st.session_state.perplexity_webui_stream_complete = False
        st.session_state.perplexity_api_stream_complete = False
        st.session_state.perplexity_concurrent_streaming_active = False
        st.session_state.perplexity_generating_response = False
        st.session_state.perplexity_generating_api_response = False
        st.session_state.perplexity_processed_transcription = None  # Reset processed transcription

        # Clear Gemini responses for new recording
        st.session_state.gemini_response = None
        st.session_state.gemini_api_response = None
        st.session_state.gemini_webui_streaming_text = ""
        st.session_state.gemini_api_streaming_text = ""
        st.session_state.gemini_webui_stream_complete = False
        st.session_state.gemini_api_stream_complete = False
        st.session_state.gemini_concurrent_streaming_active = False
        st.session_state.gemini_generating_response = False
        st.session_state.gemini_generating_api_response = False
        st.session_state.gemini_processed_transcription = None  # Reset processed transcription

        audio_q  = queue.Queue()
        frames   = []
        stop_evt = threading.Event()

        st.session_state.curr_audio_q  = audio_q
        st.session_state.curr_frames   = frames
        st.session_state.curr_stop_evt = stop_evt

        threading.Thread(
            target=record_worker,
            args=(stop_evt, audio_q, frames),
            daemon=True
        ).start()

        st.success("Recording…")
        st.rerun()                # refresh so the label flips to "⏹️ Stop"

    else:                                     # ───── STOP branch ─────
        st.session_state.recording = False
        st.session_state.curr_stop_evt.set()
        threading.Event().wait(0.3)           # let buffer flush

        wav_path = save_wav(st.session_state.curr_frames)
        st.session_state.last_wav = wav_path
        st.session_state.curr_frames.clear()

        if wav_path:
            st.success(f"Saved: **{wav_path}**")
            if st.session_state.auto_transcribe:
                st.session_state.transcribing = True
                st.session_state.transcription = None
                st.rerun()        # show "transcribing…" state
        else:
            st.error("No audio captured")

        st.rerun()                # refresh so the label flips to "▶️ Start"


# ---------- Playback ----------
if st.session_state.last_wav:
    st.audio(open(st.session_state.last_wav, "rb").read(),
             format="audio/wav")

# ---------- Transcription ----------
if st.session_state.last_wav and not st.session_state.recording:
    col_transcribe, col_status = st.columns([1, 2])
    
    with col_transcribe:
        if st.button("📝 Transcribe", disabled=st.session_state.transcribing):
            st.session_state.transcribing = True
            st.session_state.transcription = None
            
            with st.spinner("Transcribing audio..."):
                transcript = transcribe_audio_file(st.session_state.last_wav)
                st.session_state.transcription = transcript
                st.session_state.transcribing = False
    
    with col_status:
        if st.session_state.transcribing:
            st.info("🔄 Transcribing...")
        elif st.session_state.transcription:
            st.success("✅ Transcription complete")

    # Display transcription result with form for Ctrl+Enter functionality
    if st.session_state.transcription:
        with st.form("transcription_form", clear_on_submit=False):
            st.subheader("📄 Transcription")
            
            # Text area that user can edit - Ctrl+Enter will submit the form
            edited_text = st.text_area(
                "Transcribed Text:",
                value=current_transcription(),
                height=100,
                key="transcription_display"
            )
            
            # Form submit button - triggered by Ctrl+Enter or clicking
            col_submit, col_stop = st.columns([2, 1])
            
            with col_submit:
                submitted = st.form_submit_button("💬 Get AI Response (Ctrl+Enter)", disabled=st.session_state.generating_response)
            
            with col_stop:
                # Stop button outside form since it needs immediate action
                pass
        
        # Stop button outside the form for immediate response
        if (st.session_state.generating_response or 
            st.session_state.claude_generating_response or 
            st.session_state.claude_generating_api_response or
            st.session_state.grok_generating_response or 
            st.session_state.grok_generating_api_response or
            st.session_state.perplexity_generating_response or 
            st.session_state.perplexity_generating_api_response or
            st.session_state.gemini_generating_response or 
            st.session_state.gemini_generating_api_response):
            if st.button("🛑 Stop All Streaming", key="main_stop_streaming"):
                st.session_state.stop_streaming = True
                st.session_state.generating_response = False
                st.session_state.claude_generating_response = False
                st.session_state.claude_generating_api_response = False
                st.session_state.claude_concurrent_streaming_active = False
                st.session_state.grok_generating_response = False
                st.session_state.grok_generating_api_response = False
                st.session_state.grok_concurrent_streaming_active = False
                st.session_state.perplexity_generating_response = False
                st.session_state.perplexity_generating_api_response = False
                st.session_state.perplexity_concurrent_streaming_active = False
                st.session_state.gemini_generating_response = False
                st.session_state.gemini_generating_api_response = False
                st.session_state.gemini_concurrent_streaming_active = False
                st.rerun()
        
        # Handle form submission (Ctrl+Enter or button click)  
        if submitted and not st.session_state.generating_response:
            question = current_transcription()
            # Start streaming for enabled models only
            if st.session_state.enable_chatgpt_webui or st.session_state.enable_chatgpt_api:
                chatgpt_start_concurrent_streaming(question)
            if st.session_state.enable_claude_webui or st.session_state.enable_claude_api:
                claude_start_concurrent_streaming(question)
            if st.session_state.enable_grok_webui or st.session_state.enable_grok_api:
                grok_start_concurrent_streaming(question)
            if st.session_state.enable_perplexity_webui or st.session_state.enable_perplexity_api:
                perplexity_start_concurrent_streaming(question)
            if st.session_state.enable_gemini_webui or st.session_state.enable_gemini_api:
                gemini_start_concurrent_streaming(question)
            st.rerun()

# Create tabs for ChatGPT, Claude, Grok, and Perplexity responses
if st.session_state.transcription and not st.session_state.recording:
    st.subheader("🤖 AI Responses")
    
    # Create tabs only for enabled models
    tab_names = []
    if st.session_state.enable_chatgpt_webui or st.session_state.enable_chatgpt_api:
        tab_names.append("💬 ChatGPT")
    if st.session_state.enable_claude_webui or st.session_state.enable_claude_api:
        tab_names.append("🤖 Claude")
    if st.session_state.enable_grok_webui or st.session_state.enable_grok_api:
        tab_names.append("🚀 Grok")
    if st.session_state.enable_perplexity_webui or st.session_state.enable_perplexity_api:
        tab_names.append("🔍 Perplexity")
    if st.session_state.enable_gemini_webui or st.session_state.enable_gemini_api:
        tab_names.append("💎 Gemini")
    
    if tab_names:
        tabs = st.tabs(tab_names)
        tab_index = 0
        
        if st.session_state.enable_chatgpt_webui or st.session_state.enable_chatgpt_api:
            with tabs[tab_index]:
                render_chatgpt_responses()
            tab_index += 1
        
        if st.session_state.enable_claude_webui or st.session_state.enable_claude_api:
            with tabs[tab_index]:
                render_claude_responses()
            tab_index += 1
        
        if st.session_state.enable_grok_webui or st.session_state.enable_grok_api:
            with tabs[tab_index]:
                render_grok_responses()
            tab_index += 1
        
        if st.session_state.enable_perplexity_webui or st.session_state.enable_perplexity_api:
            with tabs[tab_index]:
                render_perplexity_responses()
            tab_index += 1
        
        if st.session_state.enable_gemini_webui or st.session_state.enable_gemini_api:
            with tabs[tab_index]:
                render_gemini_responses()
    else:
        st.info("Please enable at least one AI model using the checkboxes above.")

# ---------- Auto-transcription handler ----------
if (st.session_state.transcribing and 
    st.session_state.last_wav and 
    not st.session_state.recording and 
    st.session_state.transcription is None):
    
    with st.spinner("Auto-transcribing audio..."):
        transcript = transcribe_audio_file(st.session_state.last_wav)
        st.session_state.transcription = transcript
        st.session_state.transcribing = False
        
    if transcript:
        st.success("✅ Auto-transcription complete")
        
        # Automatically start concurrent streaming based on auto settings
        question = current_transcription()
        
        # Start ChatGPT streaming if auto_chatgpt is enabled
        if (st.session_state.auto_chatgpt and 
            (st.session_state.enable_chatgpt_webui or st.session_state.enable_chatgpt_api) and 
            not st.session_state.concurrent_streaming_active):
            chatgpt_start_concurrent_streaming(question)
        
        # Start Claude streaming if auto_claude is enabled
        if (st.session_state.auto_claude and 
            (st.session_state.enable_claude_webui or st.session_state.enable_claude_api) and 
            not st.session_state.claude_concurrent_streaming_active):
            claude_start_concurrent_streaming(question)
        
        # Start Grok streaming if auto_grok is enabled
        if (st.session_state.auto_grok and 
            (st.session_state.enable_grok_webui or st.session_state.enable_grok_api) and 
            not st.session_state.grok_concurrent_streaming_active):
            grok_start_concurrent_streaming(question)
        
        # Start Perplexity streaming if auto_perplexity is enabled OR if API is enabled (immediate start)
        if ((st.session_state.auto_perplexity or st.session_state.enable_perplexity_api) and 
            (st.session_state.enable_perplexity_webui or st.session_state.enable_perplexity_api) and 
            not st.session_state.perplexity_concurrent_streaming_active):
            perplexity_start_concurrent_streaming(question)
        
        # Start Gemini streaming if auto_gemini is enabled
        if (st.session_state.auto_gemini and 
            (st.session_state.enable_gemini_webui or st.session_state.enable_gemini_api) and 
            not st.session_state.gemini_concurrent_streaming_active):
            gemini_start_concurrent_streaming(question)
        
        st.rerun()  # Single rerun is enough

# Centralized streaming refresh logic
def handle_all_streaming():
    """Centralized handler for all streaming activities"""
    any_streaming = False
    
    # Check ChatGPT streaming status
    if st.session_state.concurrent_streaming_active:
        any_streaming = True
        # Check if both ChatGPT streams are complete
        if st.session_state.webui_stream_complete and st.session_state.api_stream_complete:
            st.session_state.concurrent_streaming_active = False
            
            # Log both responses when both streams are complete
            if st.session_state.pending_log_question:
                from chat_handlers.chatgpt_handler import log_qa_pair
                log_qa_pair(
                    st.session_state.pending_log_question,
                    webui_answer=st.session_state.chatgpt_response,
                    api_answer=st.session_state.api_response,
                    webui_question=st.session_state.pending_log_webui_question,
                    api_question=st.session_state.pending_log_api_question
                )
                # Clear after logging
                st.session_state.pending_log_question = None
                st.session_state.pending_log_webui_question = None
                st.session_state.pending_log_api_question = None
            
            st.success("✅ ChatGPT responses completed!")
    
    # Check Claude streaming status
    if st.session_state.claude_concurrent_streaming_active:
        any_streaming = True
        # Check if both Claude streams are complete
        if st.session_state.claude_webui_stream_complete and st.session_state.claude_api_stream_complete:
            st.session_state.claude_concurrent_streaming_active = False
            
            # Log both responses when both streams are complete
            if st.session_state.claude_pending_log_question:
                from chat_handlers.claude_handler import log_qa_pair as claude_log_qa_pair
                claude_log_qa_pair(
                    st.session_state.claude_pending_log_question,
                    webui_answer=st.session_state.claude_response,
                    api_answer=st.session_state.claude_api_response,
                    webui_question=st.session_state.claude_pending_log_webui_question,
                    api_question=st.session_state.claude_pending_log_api_question
                )
                # Clear after logging
                st.session_state.claude_pending_log_question = None
                st.session_state.claude_pending_log_webui_question = None
                st.session_state.claude_pending_log_api_question = None
            
            st.success("✅ Claude responses completed!")
    
    # Check Grok streaming status
    if st.session_state.grok_concurrent_streaming_active:
        any_streaming = True
        # Check if both Grok streams are complete
        if st.session_state.grok_webui_stream_complete and st.session_state.grok_api_stream_complete:
            st.session_state.grok_concurrent_streaming_active = False
            
            # Log both responses when both streams are complete
            if st.session_state.grok_pending_log_question:
                from chat_handlers.grok_handler import log_qa_pair as grok_log_qa_pair
                grok_log_qa_pair(
                    st.session_state.grok_pending_log_question,
                    webui_answer=st.session_state.grok_response,
                    api_answer=st.session_state.grok_api_response,
                    webui_question=st.session_state.grok_pending_log_webui_question,
                    api_question=st.session_state.grok_pending_log_api_question
                )
                # Clear after logging
                st.session_state.grok_pending_log_question = None
                st.session_state.grok_pending_log_webui_question = None
                st.session_state.grok_pending_log_api_question = None
            
            st.success("✅ Grok responses completed!")
    
    # Check Perplexity streaming status
    if st.session_state.perplexity_concurrent_streaming_active:
        any_streaming = True
        # Check if both Perplexity streams are complete
        if st.session_state.perplexity_webui_stream_complete and st.session_state.perplexity_api_stream_complete:
            st.session_state.perplexity_concurrent_streaming_active = False
            
            # Log both responses when both streams are complete
            if st.session_state.perplexity_pending_log_question:
                from chat_handlers.perplexity_handler import log_qa_pair as perplexity_log_qa_pair
                perplexity_log_qa_pair(
                    st.session_state.perplexity_pending_log_question,
                    webui_answer=st.session_state.perplexity_response,
                    api_answer=st.session_state.perplexity_api_response,
                    webui_question=st.session_state.perplexity_pending_log_webui_question,
                    api_question=st.session_state.perplexity_pending_log_api_question
                )
                # Clear after logging
                st.session_state.perplexity_pending_log_question = None
                st.session_state.perplexity_pending_log_webui_question = None
                st.session_state.perplexity_pending_log_api_question = None
            
            st.success("✅ Perplexity responses completed!")
    
    # Check Gemini streaming status
    if st.session_state.gemini_concurrent_streaming_active:
        any_streaming = True
        # Check if both Gemini streams are complete
        if st.session_state.gemini_webui_stream_complete and st.session_state.gemini_api_stream_complete:
            st.session_state.gemini_concurrent_streaming_active = False
            
            # Log both responses when both streams are complete
            if st.session_state.gemini_pending_log_question:
                from chat_handlers.gemini_handler import log_qa_pair as gemini_log_qa_pair
                gemini_log_qa_pair(
                    st.session_state.gemini_pending_log_question,
                    webui_answer=st.session_state.gemini_response,
                    api_answer=st.session_state.gemini_api_response,
                    webui_question=st.session_state.gemini_pending_log_webui_question,
                    api_question=st.session_state.gemini_pending_log_api_question
                )
                # Clear after logging
                st.session_state.gemini_pending_log_question = None
                st.session_state.gemini_pending_log_webui_question = None
                st.session_state.gemini_pending_log_api_question = None
            
            st.success("✅ Gemini responses completed!")
    
    # Auto-refresh if any streaming is active
    if any_streaming:
        import time
        time.sleep(0.2)  # Refresh every 200ms for smoother streaming
        st.rerun()

# Handle centralized streaming logic
handle_all_streaming()

# Handle stopped streaming using the imported modules
chatgpt_handle_stopped_streaming()
claude_handle_stopped_streaming()
grok_handle_stopped_streaming()
perplexity_handle_stopped_streaming()
gemini_handle_stopped_streaming()

# Smart Auto-start Perplexity API if enabled and transcription is available
if (st.session_state.enable_perplexity_api and 
    st.session_state.transcription and 
    not st.session_state.recording):
    
    question = current_transcription()
    if question and question.strip():
        # Only start if we haven't processed this transcription yet and we're not already streaming
        if (not st.session_state.perplexity_concurrent_streaming_active and
            not st.session_state.perplexity_generating_api_response and
            st.session_state.perplexity_processed_transcription != question):
            
            print(f"DEBUG: Smart Auto-starting Perplexity API for new question: {question[:50]}...")
            print(f"DEBUG: concurrent_active={st.session_state.perplexity_concurrent_streaming_active}")
            print(f"DEBUG: generating_api={st.session_state.perplexity_generating_api_response}")
            print(f"DEBUG: processed_transcription={st.session_state.perplexity_processed_transcription}")
            
            # Mark this transcription as processed to prevent re-triggering
            st.session_state.perplexity_processed_transcription = question
            perplexity_start_concurrent_streaming(question)
            st.rerun()

# live status
if st.session_state.recording:
    st.markdown("🔴 **Recording...** Press Stop when done.")
