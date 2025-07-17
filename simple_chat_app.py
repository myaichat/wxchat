# simple_chat_app.py  –  thread‑safe Streamlit mic recorder with direct streaming_chat calls
import streamlit as st

# Configure page layout to be wide
st.set_page_config(
    page_title="SpeakStream AI",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for tab-like headers with much smaller styling
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

# Import the streaming function directly
from streaming_chat import send_message_with_streaming

# Load environment variables from .env file
load_dotenv(dotenv_path=Path(".") / ".env", override=True)

RATE, CH = 16_000, 1
OUT_DIR  = "recordings"
os.makedirs(OUT_DIR, exist_ok=True)

TIMEOUT_SEC = 60

# Logging configuration
LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

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
if "chatgpt_response" not in st.session_state:
    st.session_state.chatgpt_response = None
if "generating_response" not in st.session_state:
    st.session_state.generating_response = False
if "selected_model" not in st.session_state:
    st.session_state.selected_model = "gpt-4o"  # default model
if "auto_chatgpt" not in st.session_state:
    st.session_state.auto_chatgpt = True  # auto ChatGPT enabled by default
if "stop_streaming" not in st.session_state:
    st.session_state.stop_streaming = False  # flag to stop streaming
if "manual_transcription" not in st.session_state:
    st.session_state.manual_transcription = None  # store manual transcription for processing
if "session_log_file" not in st.session_state:
    # Create a unique log file for this session
    session_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.session_log_file = os.path.join(LOGS_DIR, f"chat_session_{session_timestamp}.json")
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

# Modified helper function for concurrent streaming
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
    
    # Start Web UI streaming thread (now using direct streaming_chat)
    start_thread(webui_streaming_worker, question)
    
    # Start API streaming thread  
    start_thread(api_streaming_worker, question)

def webui_streaming_worker(question):
    """Worker thread for Web UI streaming using direct streaming_chat - updates session state incrementally"""
    try:
        # Store original prompt for logging
        original_prompt = question.strip()
        cleaned_prompt = original_prompt + ". Answer in clean raw markdown without citations."
        
        # Add to conversation history
        st.session_state.conversation_history.append({"role": "user", "content": cleaned_prompt})
        
        full_response = ""
        previous = ""
        response_started = False
        
        # Create event loop for async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Use the direct streaming function
            async def stream_response():
                nonlocal full_response, previous, response_started
                
                async for chunk in send_message_with_streaming(cleaned_prompt, TIMEOUT_SEC):
                    if st.session_state.stop_streaming:
                        break
                    
                    status = chunk.get("status")
                    content = chunk.get("content", "")
                    
                    if status == "started":
                        response_started = True
                        st.session_state.webui_streaming_text = "🚀 Assistant started typing..."
                    elif status == "streaming":
                        # Update session state with streaming content
                        if len(content) > len(previous):
                            # Smart streaming logic (same as simple_ask_chatgpt.py)
                            safe_patterns = [
                                '\n\n', '\n- ', '\n## ', '\n### ', '. ', '! ', '? ', 
                                ', ', '; ', ': ', '**.', '**,', '**:', '`.', '`,', '```\n'
                            ]
                            
                            last_safe_pos = len(previous)
                            for pattern in safe_patterns:
                                pos = content.rfind(pattern, len(previous))
                                if pos != -1 and pos + len(pattern) > last_safe_pos:
                                    last_safe_pos = pos + len(pattern)
                            
                            space_pos = content.rfind(' ', len(previous))
                            if space_pos != -1 and space_pos + 1 > last_safe_pos:
                                check_pos = space_pos + 1
                                if check_pos < len(content):
                                    before_space = content[max(0, space_pos-5):space_pos]
                                    after_space = content[space_pos:min(len(content), space_pos+5)]
                                    if not ('**' in before_space and '**' not in after_space) and not ('`' in before_space and '`' not in after_space):
                                        last_safe_pos = check_pos
                            
                            if last_safe_pos > len(previous) + 15:
                                new_chunk = content[len(previous):last_safe_pos]
                                full_response += new_chunk
                                # Update session state for UI display
                                st.session_state.webui_streaming_text = full_response + "▌"
                                previous = content[:last_safe_pos]
                            elif len(content) > len(previous) + 150:
                                force_pos = len(previous) + 100
                                last_space = content.rfind(' ', len(previous), force_pos)
                                if last_space > len(previous):
                                    new_chunk = content[len(previous):last_space + 1]
                                    full_response += new_chunk
                                    st.session_state.webui_streaming_text = full_response + "▌"
                                    previous = content[:last_space + 1]
                    elif status == "complete":
                        if len(content) > len(previous):
                            remaining = content[len(previous):]
                            full_response += remaining
                        elif not response_started:
                            full_response = content
                        
                        # Final update to session state
                        st.session_state.webui_streaming_text = full_response
                        break
                    elif status in ["timeout", "error"]:
                        st.session_state.webui_streaming_text = f"Streaming error: {content}"
                        st.session_state.webui_stream_complete = True
                        st.session_state.generating_response = False
                        return
            
            # Run the async streaming
            loop.run_until_complete(stream_response())
            
        finally:
            loop.close()
        
        # Store final response
        if full_response:
            st.session_state.conversation_history.append({"role": "assistant", "content": full_response})
            st.session_state.chatgpt_response = full_response
            # Log the Q&A pair
            log_qa_pair(original_prompt, full_response)
        
        st.session_state.webui_stream_complete = True
        st.session_state.generating_response = False
        
    except Exception as e:
        st.session_state.webui_streaming_text = f"Error: {str(e)}"
        st.session_state.webui_stream_complete = True
        st.session_state.generating_response = False

def api_streaming_worker(question):
    """Worker thread for API streaming - updates session state incrementally"""
    try:
        from openai import OpenAI
        import os
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Add to conversation history (separate copy for API)
        messages = st.session_state.conversation_history + [{"role": "user", "content": question}]
        
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
                # Update session state with cursor
                st.session_state.api_streaming_text = full_response + "▌"
        
        # Final update without cursor
        st.session_state.api_streaming_text = full_response
        st.session_state.api_response = full_response
        
        st.session_state.api_stream_complete = True
        st.session_state.generating_api_response = False
        
    except Exception as e:
        st.session_state.api_streaming_text = f"Error: {str(e)}"
        st.session_state.api_stream_complete = True
        st.session_state.generating_api_response = False

def get_chatgpt_response(prompt, show_streaming=True, container=None):
    """Get streaming response from ChatGPT"""
    try:
        from openai import OpenAI
        import os
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        st.session_state.conversation_history.append({"role": "user", "content": prompt})
        
        # Where to print?
        if show_streaming:
            if container:
                with container:
                    response_placeholder = st.empty()
            else:
                response_placeholder = st.empty()
        else:
            response_placeholder = None
        full_response = ""
        
        # Reset stop streaming flag
        st.session_state.stop_streaming = False
        
        # Stream the response
        stream = client.chat.completions.create(
            model=st.session_state.selected_model,
            messages=st.session_state.conversation_history,
            stream=True
        )
        
        for chunk in stream:
            # Check if user requested to stop streaming
            if st.session_state.stop_streaming:
                if show_streaming and response_placeholder:
                    # Clean Unicode surrogates before displaying
                    clean_response = full_response.encode('utf-8', errors='replace').decode('utf-8')
                    response_placeholder.markdown(clean_response + "\n\n*[Streaming stopped by user]*")
                break
                
            if chunk.choices[0].delta.content is not None:
                full_response += chunk.choices[0].delta.content
                if show_streaming and response_placeholder:
                    # Clean Unicode surrogates before displaying
                    clean_response = full_response.encode('utf-8', errors='replace').decode('utf-8')
                    response_placeholder.markdown(clean_response + "▌")
        
        # Remove the cursor and show final response (if not stopped)
        if not st.session_state.stop_streaming and show_streaming and response_placeholder:
            # Clean Unicode surrogates before displaying
            clean_response = full_response.encode('utf-8', errors='replace').decode('utf-8')
            response_placeholder.markdown(clean_response)
        
        # Add the complete response to conversation history
        if full_response:
            st.session_state.conversation_history.append({"role": "assistant", "content": full_response})
        
        return full_response
    except Exception as e:
        st.error(f"ChatGPT API error: {str(e)}")
        return None

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

# ---------- Settings ----------
settings_col1, settings_col2 = st.columns(2)

with settings_col1:
    st.session_state.auto_transcribe = st.checkbox("🤖 Auto-transcribe after recording", 
                                                   value=st.session_state.auto_transcribe)

with settings_col2:
    st.session_state.auto_chatgpt = st.checkbox("🤖 Auto ChatGPT", 
                                               value=st.session_state.auto_chatgpt)

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
                submitted = st.form_submit_button("💬 Get ChatGPT Response (Ctrl+Enter)", disabled=st.session_state.generating_response)
            
            with col_stop:
                # Stop button outside form since it needs immediate action
                pass
        
        # Stop button outside the form for immediate response
        if st.session_state.generating_response:
            if st.button("🛑 Stop Streaming"):
                st.session_state.stop_streaming = True
                st.session_state.generating_response = False
                st.rerun()
        
        # Handle form submission (Ctrl+Enter or button click)  
        if submitted and not st.session_state.generating_response:
            question = current_transcription()
            start_concurrent_streaming(question)  # Use concurrent streaming
            st.rerun()

# Modified ChatGPT Response section with concurrent streaming
if st.session_state.transcription and not st.session_state.recording:
    st.subheader("🤖 ChatGPT Response")

    # Show generating status
    if st.session_state.generating_response or st.session_state.generating_api_response:
        active_streams = []
        if st.session_state.generating_response:
            active_streams.append("Web UI")
        if st.session_state.generating_api_response:
            active_streams.append("API")
        st.info(f"🔄 Generating responses: {', '.join(active_streams)}")

    # Stop button for concurrent streaming - placed above columns
    if st.session_state.concurrent_streaming_active:
        if st.button("🛑 Stop All Streaming"):
            st.session_state.stop_streaming = True
            st.session_state.concurrent_streaming_active = False
            st.session_state.generating_response = False
            st.session_state.generating_api_response = False
            st.rerun()

    # Two side-by-side panes with concurrent streaming
    col_web, col_api = st.columns(2)

    # Web UI pane
    with col_web:
        st.markdown('<div class="box-header">🌐 Web UI</div>', unsafe_allow_html=True)
        
        remove='markdown\nCopy\nEdit\n'
        if st.session_state.webui_streaming_text:
            # Show live streaming updates
            st.markdown(st.session_state.webui_streaming_text.strip(remove))
        elif st.session_state.chatgpt_response and not st.session_state.concurrent_streaming_active:
            # Show final response when not streaming
            clean = st.session_state.chatgpt_response.encode("utf-8", errors="replace").decode("utf-8")
            st.markdown(clean.strip(remove))
        elif st.session_state.generating_response:
            st.info("Response will appear here…")
        else:
            st.info("Click **Get Both Responses** to generate responses")

    # API pane
    with col_api:
        st.markdown('<div class="box-header">⚡ API</div>', unsafe_allow_html=True)
        
        if st.session_state.api_streaming_text:
            # Show live streaming updates
            st.markdown(st.session_state.api_streaming_text)
        elif st.session_state.api_response and not st.session_state.concurrent_streaming_active:
            # Show final response when not streaming
            st.markdown(st.session_state.api_response)
        elif st.session_state.generating_api_response:
            st.info("API response will appear here…")
        else:
            st.info("Responses will appear here")

# Auto-refresh during concurrent streaming with better timing
if st.session_state.concurrent_streaming_active:
    # Check if both streams are complete
    if st.session_state.webui_stream_complete and st.session_state.api_stream_complete:
        st.session_state.concurrent_streaming_active = False
        st.success("✅ Both responses completed!")
        st.rerun()
    else:
        # More frequent auto-refresh during active streaming
        import time
        time.sleep(0.2)  # Refresh every 200ms for smoother streaming
        st.rerun()

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
        
        # Automatically start concurrent streaming if auto_chatgpt is enabled
        if st.session_state.auto_chatgpt and not st.session_state.concurrent_streaming_active:
            question = current_transcription()
            start_concurrent_streaming(question)
        
        st.rerun()  # Single rerun is enough

# ---------- Handle stopped streaming ----------
if st.session_state.stop_streaming and (st.session_state.generating_response or st.session_state.generating_api_response):
    st.session_state.generating_response = False
    st.session_state.generating_api_response = False
    st.session_state.stop_streaming = False
    st.session_state.manual_transcription = None  # Clear manual transcription if stopped
    st.info("🛑 Streaming stopped by user")

# live status
if st.session_state.recording:
    st.markdown("🔴 **Recording...** Press Stop when done.")
