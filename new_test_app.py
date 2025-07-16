import streamlit as st
import asyncio
import sounddevice as sd
import numpy as np
import wave
import os
import queue
import threading
import datetime
from pathlib import Path
from dotenv import load_dotenv
from include.transcribe import Transcribe
from streaming_chat import send_message_with_streaming

# Load environment variables from .env file
load_dotenv(dotenv_path=Path(".") / ".env", override=True)

# Audio recording constants
RATE, CH = 16_000, 1
OUT_DIR = "recordings"
os.makedirs(OUT_DIR, exist_ok=True)

# ───────────────────── session defaults ─────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "streaming_response" not in st.session_state:
    st.session_state.streaming_response = ""
if "is_streaming" not in st.session_state:
    st.session_state.is_streaming = False
if "chat_input_value" not in st.session_state:
    st.session_state.chat_input_value = ""

if "recording" not in st.session_state:
    st.session_state.recording = False
if "last_wav" not in st.session_state:
    st.session_state.last_wav = None

if "transcription" not in st.session_state:
    st.session_state.transcription = None
if "transcribing" not in st.session_state:
    st.session_state.transcribing = False
if "transcriber" not in st.session_state:
    st.session_state.transcriber = None
if "auto_transcribe" not in st.session_state:
    st.session_state.auto_transcribe = True

# ───────────────────── recording helpers ─────────────────────
def record_worker(stop_evt: threading.Event, audio_q: queue.Queue, frames: list[np.ndarray]):
    """Background worker; never touches Streamlit objects."""

    def _callback(indata, *_):
        audio_q.put(indata.copy())

    with sd.InputStream(samplerate=RATE, channels=CH, dtype="int16", callback=_callback):
        while not stop_evt.is_set():
            try:
                frames.append(audio_q.get(timeout=0.1))
            except queue.Empty:
                pass

def save_wav(frames) -> str | None:
    if not frames:
        return None
    pcm = np.concatenate(frames).tobytes()

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(OUT_DIR, f"{ts}.wav")
    with wave.open(path, "wb") as wf:
        wf.setnchannels(CH)
        wf.setsampwidth(2)  # int16
        wf.setframerate(RATE)
        wf.writeframes(pcm)
    return path

# ───────────────────── transcription helpers ─────────────────────
def transcribe_audio_file(audio_path: str) -> str | None:
    try:
        if st.session_state.transcriber is None:
            st.session_state.transcriber = Transcribe()
        return st.session_state.transcriber.transcribe_audio(audio_path)
    except Exception as e:
        st.error(f"Transcription failed: {str(e)}")
        return None


def current_transcription() -> str | None:
    """Always return the text the user sees/edits."""
    return st.session_state.get("transcription_display", st.session_state.transcription)

# ───────────────────── layout ─────────────────────
st.title("🚀 Streaming Chat Test with Voice Recording & Transcription")
st.write("Test the streaming chat functionality")

st.subheader("🎙️ Voice Recording")
st.session_state.auto_transcribe = st.checkbox(
    "🤖 Auto-transcribe after recording", value=st.session_state.auto_transcribe
)

label = "▶️ Start Recording" if not st.session_state.recording else "⏹️ Stop Recording"

if st.button(label, key="rec_toggle"):
    if not st.session_state.recording:  # START
        st.session_state.recording = True
        st.session_state.last_wav = None

        audio_q = queue.Queue()
        frames = []
        stop_evt = threading.Event()

        st.session_state.curr_audio_q = audio_q
        st.session_state.curr_frames = frames
        st.session_state.curr_stop_evt = stop_evt

        threading.Thread(
            target=record_worker,
            args=(stop_evt, audio_q, frames),
            daemon=True,
        ).start()

        st.success("🔴 Recording…")
        st.rerun()
    else:  # STOP
        st.session_state.recording = False
        st.session_state.curr_stop_evt.set()
        threading.Event().wait(0.3)

        wav_path = save_wav(st.session_state.curr_frames)
        st.session_state.last_wav = wav_path
        st.session_state.curr_frames.clear()

        if wav_path:
            st.success(f"✅ Saved: **{wav_path}**")
            st.session_state.transcription = None
            st.session_state.transcribing = False
            if st.session_state.auto_transcribe:
                st.session_state.transcribing = True
        else:
            st.error("❌ No audio captured")
        st.rerun()

# Recording status
if st.session_state.recording:
    st.markdown("🔴 **Recording…** Press Stop when done.")

# Playback
if st.session_state.last_wav:
    st.subheader("🔊 Playback")
    st.audio(open(st.session_state.last_wav, "rb").read(), format="audio/wav")

# ───────────────────── transcription UI ─────────────────────
if st.session_state.last_wav and not st.session_state.recording:
    st.subheader("📝 Transcription")

    col_transcribe, col_status = st.columns([1, 2])
    with col_transcribe:
        if st.button("📝 Transcribe", disabled=st.session_state.transcribing):
            st.session_state.transcribing = True
            st.session_state.transcription = None
            st.rerun()

    with col_status:
        if st.session_state.transcribing:
            st.info("🔄 Transcribing…")
        elif st.session_state.transcription:
            st.success("✅ Transcription complete")

    if st.session_state.transcription:
        transcribed_text = st.text_area(
            "Transcribed Text:",
            value=current_transcription(),
            height=100,
            key="transcription_display",
        )
        if st.button("💬 Send to Chat", key="send_transcription"):
            if transcribed_text.strip():
                st.session_state.chat_input_value = transcribed_text
                st.rerun()

st.divider()

# ───────────────────── chat area ─────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

with st.form("chat_form", clear_on_submit=True):
    question = st.text_input(
        "Enter your question:",
        value=st.session_state.chat_input_value,
        placeholder="Ask me anything…",
    )
    submitted = st.form_submit_button("Send", disabled=st.session_state.is_streaming)


def handle_chat_message(message_text: str):
    with st.chat_message("user"):
        st.write(message_text)
    with st.chat_message("assistant"):
        placeholder = st.empty()

        async def stream():
            full = ""
            try:
                async for res in send_message_with_streaming(message_text, timeout=60):
                    status = res.get("status", "")
                    content = res.get("content", "")
                    if status == "started":
                        placeholder.markdown("🔄 Starting response…")
                    elif status == "streaming":
                        full = content
                        placeholder.markdown(full + "▌")
                    elif status == "complete":
                        full = content
                        placeholder.markdown(full)
                        break
                    elif status in {"timeout", "error"}:
                        err = f"❌ Error: {content}" if content else "❌ Request failed"
                        placeholder.markdown(err)
                        full = err
                        break
                return full
            except Exception as e:
                err = f"❌ Exception: {e}"
                placeholder.markdown(err)
                return err

        try:
            final = asyncio.run(stream())
            if final:
                st.session_state.messages.append({"role": "assistant", "content": final})
        except Exception as e:
            err = f"❌ Failed: {e}"
            placeholder.markdown(err)
            st.session_state.messages.append({"role": "assistant", "content": err})
        finally:
            st.session_state.is_streaming = False
            st.rerun()

# ───────────────────── form submission ─────────────────────
if submitted and question and not st.session_state.is_streaming:
    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.chat_input_value = ""
    st.session_state.is_streaming = True
    st.session_state.streaming_response = ""
    handle_chat_message(question)

if st.session_state.is_streaming and st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    handle_chat_message(st.session_state.messages[-1]["content"])

if st.session_state.is_streaming:
    st.info("🔄 Streaming response…")

if st.button("Clear Chat"):
    st.session_state.messages = []
    st.session_state.streaming_response = ""
    st.session_state.is_streaming = False
    st.rerun()

# ───────────────────── transcription handlers ─────────────────────
if (
    st.session_state.transcribing
    and st.session_state.last_wav
    and not st.session_state.recording
    and st.session_state.transcription is None
):
    with st.spinner("Transcribing audio…"):
        transcript = transcribe_audio_file(st.session_state.last_wav)
    st.session_state.transcription = transcript
    st.session_state.chat_input_value = transcript or ""
    st.session_state.transcribing = False
    st.rerun()

if (
    st.session_state.auto_transcribe
    and st.session_state.last_wav
    and not st.session_state.recording
    and not st.session_state.transcribing
    and st.session_state.transcription is None
):
    st.session_state.transcribing = True
    st.rerun()
elif (
    st.session_state.transcription
    and st.session_state.chat_input_value == ""
):
    st.session_state.chat_input_value = st.session_state.transcription

# ───────────────────── debug ─────────────────────
with st.expander("Debug Info"):
    st.json(
        {
            "messages_count": len(st.session_state.messages),
            "is_streaming": st.session_state.is_streaming,
            "streaming_response_length": len(st.session_state.streaming_response),
            "recording": st.session_state.recording,
            "last_wav": st.session_state.last_wav,
            "transcription": st.session_state.transcription,
            "transcribing": st.session_state.transcribing,
            "auto_transcribe": st.session_state.auto_transcribe,
        }
    )
