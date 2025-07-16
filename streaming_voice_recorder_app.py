# voice_recorder_app.py  –  thread‑safe Streamlit mic recorder
import streamlit as st
import sounddevice as sd
import numpy as np
import wave, os, io, queue, threading, datetime
import asyncio
from include.transcribe import Transcribe
from pathlib import Path
from dotenv import load_dotenv
from streaming_chat import send_message_with_streaming

# Load environment variables from .env file
load_dotenv(dotenv_path=Path(".") / ".env", override=True)

RATE, CH = 16_000, 1
OUT_DIR  = "recordings"
os.makedirs(OUT_DIR, exist_ok=True)

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

# ───────────────────── helper functions ─────────────────────
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

def get_chatgpt_response(prompt):
    """Get streaming response using send_message_with_streaming"""
    try:
        # Add user message to conversation history
        st.session_state.conversation_history.append({"role": "user", "content": prompt})
        
        # Create a placeholder for streaming response
        response_placeholder = st.empty()
        
        # Stream the response using the working code from test_streaming_app.py
        async def stream_response():
            full_response = ""
            try:
                async for response in send_message_with_streaming(prompt, timeout=60):
                    # Check if user requested to stop streaming
                    if st.session_state.stop_streaming:
                        response_placeholder.markdown(full_response + "\n\n*[Streaming stopped by user]*")
                        return full_response
                    
                    status = response.get("status", "")
                    content = response.get("content", "")
                    
                    if status == "started":
                        response_placeholder.markdown("🔄 Starting response...")
                    elif status == "streaming":
                        full_response = content
                        response_placeholder.markdown(full_response + "▌")
                    elif status == "complete":
                        full_response = content
                        response_placeholder.markdown(full_response)
                        break
                    elif status in ["timeout", "error"]:
                        error_msg = f"❌ Error: {content}" if content else "❌ Request timed out or failed"
                        response_placeholder.markdown(error_msg)
                        full_response = error_msg
                        break
                        
                return full_response
            except Exception as e:
                error_msg = f"❌ Exception: {str(e)}"
                response_placeholder.markdown(error_msg)
                return error_msg
        
        # Run the async streaming function
        final_response = asyncio.run(stream_response())
        
        # Add the complete response to conversation history
        if final_response and not final_response.startswith("❌"):
            st.session_state.conversation_history.append({"role": "assistant", "content": final_response})
        
        return final_response
    except Exception as e:
        st.error(f"Streaming error: {str(e)}")
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
            st.session_state.generating_response = True
            st.session_state.chatgpt_response = None
            st.session_state.stop_streaming = False
            st.session_state.manual_transcription = edited_text  # Store for manual processing
            st.rerun()  # Refresh to show generating status

# ---------- ChatGPT Response ----------
if st.session_state.transcription and not st.session_state.recording:
    st.subheader("🤖 ChatGPT Response")
    
    # Show generating status only when in progress
    if st.session_state.generating_response:
        st.info("🔄 Generating response...")
    
    # Display ChatGPT response
    if st.session_state.chatgpt_response:
        st.markdown("**ChatGPT Response:**")
        st.markdown(st.session_state.chatgpt_response)

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
        
        # Schedule ChatGPT generation **before** rerunning
        if st.session_state.auto_chatgpt and not st.session_state.generating_response:
            st.session_state.generating_response = True
            st.session_state.chatgpt_response = None
            # ⬇️ make sure the handler sees the edited text
            st.session_state.manual_transcription = current_transcription()
        
        st.rerun()  # Single rerun is enough

# ---------- Auto-ChatGPT handler (separate from transcription) ----------
if (st.session_state.generating_response and 
    st.session_state.transcription and 
    not st.session_state.recording and 
    st.session_state.chatgpt_response is None and
    st.session_state.auto_chatgpt and
    not st.session_state.stop_streaming):
    
    with st.spinner("Auto-generating ChatGPT response..."):
        response = get_chatgpt_response(current_transcription())
        st.session_state.chatgpt_response = response
        st.session_state.generating_response = False
    
    if response:
        st.success("✅ Auto-ChatGPT response complete")
    
    st.rerun()  # Refresh to show final results

# ---------- Manual ChatGPT handler ----------
if (st.session_state.generating_response and 
    st.session_state.manual_transcription and 
    not st.session_state.recording and 
    st.session_state.chatgpt_response is None and
    not st.session_state.stop_streaming):
    
    with st.spinner("Generating ChatGPT response..."):
        response = get_chatgpt_response(current_transcription())
        st.session_state.chatgpt_response = response
        st.session_state.generating_response = False
        st.session_state.manual_transcription = None  # Clear after processing
    
    if response:
        st.success("✅ ChatGPT response complete")
    
    st.rerun()  # Refresh to show final results

# ---------- Handle stopped streaming ----------
if st.session_state.stop_streaming and st.session_state.generating_response:
    st.session_state.generating_response = False
    st.session_state.stop_streaming = False
    st.session_state.manual_transcription = None  # Clear manual transcription if stopped
    st.info("🛑 Streaming stopped by user")

# live status
if st.session_state.recording:
    st.markdown("🔴 **Recording...** Press Stop when done.")
