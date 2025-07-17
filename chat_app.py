# chat_app.py  –  thread‑safe Streamlit mic recorder with backend server API
import streamlit as st
import sounddevice as sd
import numpy as np
import wave, os, io, queue, threading, datetime
import requests
import json
from include.transcribe import Transcribe
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=Path(".") / ".env", override=True)

RATE, CH = 16_000, 1
OUT_DIR  = "recordings"
os.makedirs(OUT_DIR, exist_ok=True)

# Backend server configuration
BACKEND_URL = "http://localhost:8002/ask-chatgpt"
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

def get_chatgpt_response_backend(prompt, show_streaming=True, container=None):
    """Get streaming response from backend server API"""
    try:
        # Store original prompt for logging
        original_prompt = prompt.strip()
        
        # Clean the prompt to avoid JavaScript injection issues
        cleaned_prompt = original_prompt + ". Answer in clean raw markdown without citations."
        
        # Debug: show what we're sending only if streaming should be shown
        if show_streaming:
            if container:
                with container:
                    st.write(f"Debug: Sending message: `{repr(cleaned_prompt)}`")
            else:
                st.write(f"Debug: Sending message: `{repr(cleaned_prompt)}`")
        
        st.session_state.conversation_history.append({"role": "user", "content": cleaned_prompt})
        
        # Create a placeholder for streaming response only if streaming should be shown
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
        
        # Prepare payload for backend server (exactly like ask_chatgpt.py)
        payload = {"message": cleaned_prompt, "timeout": TIMEOUT_SEC}
        
        # Stream the response from backend server (exactly like ask_chatgpt.py)
        with requests.post(BACKEND_URL, json=payload, stream=True) as resp:
            resp.raise_for_status()
            
            previous = ""
            response_started = False
            
            for raw in resp.iter_lines(decode_unicode=True):
                # Check if user requested to stop streaming
                if st.session_state.stop_streaming:
                    if show_streaming and response_placeholder:
                        response_placeholder.markdown(full_response + "\n\n*[Streaming stopped by user]*")
                    break
                
                if not raw:  # skip keep-alives / blank lines (exactly like ask_chatgpt.py)
                    continue
                
                try:
                    data = json.loads(raw)
                    status, content = data["status"], data["content"]
                    
                    if status == "started":
                        response_started = True
                        if show_streaming and response_placeholder:
                            response_placeholder.markdown("🚀 Assistant started typing...")
                    elif status == "streaming":
                        # Only show the newly arrived chunk (like ask_chatgpt.py)
                        if len(content) > len(previous):
                            new_chunk = content[len(previous):]
                            full_response += new_chunk
                            if show_streaming and response_placeholder:
                                # Clean Unicode surrogates before displaying
                                clean_response = full_response.encode('utf-8', errors='replace').decode('utf-8')
                                response_placeholder.markdown(clean_response + "▌")
                            previous = content
                    elif status == "complete":
                        # Always show server-supplied final text (like ask_chatgpt.py)
                        if len(content) > len(previous):
                            remaining = content[len(previous):]
                            full_response += remaining
                        elif not response_started:
                            # If we never got streaming updates, show the complete content
                            full_response = content
                        
                        if show_streaming and response_placeholder:
                            # Clean Unicode surrogates before displaying
                            clean_response = full_response.encode('utf-8', errors='replace').decode('utf-8')
                            response_placeholder.markdown(clean_response)
                        break
                    elif status in ["timeout", "error"]:
                        if show_streaming:
                            if container:
                                with container:
                                    st.error(f"Backend server {status}: {content}")
                            else:
                                st.error(f"Backend server {status}: {content}")
                        return None
                        
                except json.JSONDecodeError as e:
                    if show_streaming:
                        if container:
                            with container:
                                st.error(f"JSON decode error: {e}")
                        else:
                            st.error(f"JSON decode error: {e}")
                    continue
                except Exception as e:
                    if show_streaming:
                        if container:
                            with container:
                                st.error(f"Unexpected error: {e}")
                        else:
                            st.error(f"Unexpected error: {e}")
                    continue
        
        # Add the complete response to conversation history
        if full_response:
            st.session_state.conversation_history.append({"role": "assistant", "content": full_response})
        
        return full_response, original_prompt
        
    except requests.exceptions.RequestException as e:
        if show_streaming:
            if container:
                with container:
                    st.error(f"Backend server connection error: {str(e)}")
            else:
                st.error(f"Backend server connection error: {str(e)}")
        return None
    except Exception as e:
        if show_streaming:
            if container:
                with container:
                    st.error(f"ChatGPT API error: {str(e)}")
            else:
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
    
    # Create tabs for response display - always show tabs when transcription is available
    tab1, tab2 = st.tabs(["Web UI", "API"])
    
    with tab1:
        st.markdown("**ChatGPT Response:**")
        
        # Create a container for streaming content within the Web UI tab
        webui_container = st.container()
        
        if st.session_state.chatgpt_response:
            with webui_container:
                # Clean Unicode surrogates before displaying as markdown
                clean_response = st.session_state.chatgpt_response.encode('utf-8', errors='replace').decode('utf-8')
                st.markdown(clean_response)
        elif st.session_state.generating_response:
            with webui_container:
                # Store the container in session state so streaming functions can use it
                st.session_state.webui_streaming_container = webui_container
                st.info("Response will appear here...")
        else:
            with webui_container:
                st.info("Click 'Get ChatGPT Response' to generate a response")
    
    with tab2:
        st.markdown("**API Response:**")
        # one single, always‑present placeholder
        api_container = st.container()
        st.session_state.api_streaming_container = api_container

        if st.button("🔄 Get API Response", key="api_response_btn"):
            with st.spinner("Getting API response..."):
                api_response = get_chatgpt_response(
                    current_transcription(),
                    show_streaming=True,
                    container=st.session_state.api_streaming_container,
                )
                if api_response:
                    st.session_state.api_response = api_response  # Store in session state
                    st.markdown(api_response)
                else:
                    st.error("Failed to get API response")
        elif st.session_state.api_response:
            # Display stored API response
            st.markdown(st.session_state.api_response)
        elif st.session_state.generating_api_response:
            with api_container:
                st.info("API response will appear here...")
        else:
            st.info("Click 'Get API Response' to generate a direct API response")

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
        
        # Also schedule API generation
        if st.session_state.auto_chatgpt and not st.session_state.generating_api_response:
            st.session_state.generating_api_response = True
            st.session_state.api_response = None
        
        st.rerun()  # Single rerun is enough

# ---------- Auto-ChatGPT handler (separate from transcription) ----------
if (st.session_state.generating_response and 
    st.session_state.transcription and 
    not st.session_state.recording and 
    st.session_state.chatgpt_response is None and
    st.session_state.auto_chatgpt and
    not st.session_state.stop_streaming):
    
    # Stream visibly into the Web‑UI tab
    question   = current_transcription()
    container  = st.session_state.get("webui_streaming_container", None)
    result     = get_chatgpt_response_backend(
        question,
        show_streaming=True,      # show progress!
        container=container,      # write into tab
    )
    if result:
        response, original_question = result
        st.session_state.chatgpt_response = response
        st.session_state.generating_response = False
        
        # Log the Q&A pair using original question
        if response and original_question:
            log_qa_pair(original_question, response)
    else:
        st.session_state.generating_response = False
        response = None
    
    st.rerun()  # Refresh to show final results

# ---------- Manual ChatGPT handler ----------
if (st.session_state.generating_response and 
    st.session_state.manual_transcription and 
    not st.session_state.recording and 
    st.session_state.chatgpt_response is None and
    not st.session_state.stop_streaming):
    
    # Show streaming for manual generation using the container if available
    question = current_transcription()
    container = st.session_state.get("webui_streaming_container", None)
    result = get_chatgpt_response_backend(question, show_streaming=True, container=container)
    if result:
        response, original_question = result
        st.session_state.chatgpt_response = response
        st.session_state.generating_response = False
        st.session_state.manual_transcription = None  # Clear after processing
        
        # Log the Q&A pair using original question
        if response and original_question:
            log_qa_pair(original_question, response)
    else:
        st.session_state.generating_response = False
        st.session_state.manual_transcription = None  # Clear after processing
        response = None
    
    st.rerun()  # Refresh to show final results

# ---------- Auto-API handler (separate from backend) ----------
if (st.session_state.generating_api_response and 
    st.session_state.transcription and 
    not st.session_state.recording and 
    st.session_state.api_response is None and
    st.session_state.auto_chatgpt and
    not st.session_state.stop_streaming):
    
    question   = current_transcription()
    container  = st.session_state.api_streaming_container
    api_response = get_chatgpt_response(
        question,
        show_streaming=True,      # show progress!
        container=container,      # write into API tab
    )
    if api_response:
        st.session_state.api_response = api_response
        st.session_state.generating_api_response = False
    else:
        st.session_state.generating_api_response = False
    
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
