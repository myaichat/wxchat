"""Streamlit voice recorder ➜ Whisper transcription ➜ ChatGPT answer

Esc or Page Up instantly cancels auto‑scroll; scrolling back to the bottom (<120 px) re‑enables it.

Run with:
    export OPENAI_API_KEY=...  # or set in your OS
    streamlit run voice_recorder_app.py
Requires: streamlit>=1.24, sounddevice, numpy, openai
"""
import streamlit as st
import sounddevice as sd
import numpy as np
import wave, os, queue, threading, datetime, uuid
from openai import OpenAI

RATE      = 16_000
CHANNELS  = 1
OUT_DIR   = "recordings"
os.makedirs(OUT_DIR, exist_ok=True)

# ────────────────── session defaults ──────────────────
_defaults = {
    "recording":      False,
    "frames":         [],
    "audio_q":        None,
    "stop_evt":       None,
    "last_wav":       None,
    "transcription":  None,
    "chat_history":   [],
    "chat_response":  "",
    "streaming":      False,
}
for k, v in _defaults.items():
    st.session_state.setdefault(k, v)

# ────────────────── audio helpers ─────────────────────

def _recorder(stop_evt: threading.Event, q: queue.Queue, frames: list[np.ndarray]):
    """Fill *frames* with chunks until *stop_evt* is set."""
    def _cb(indata, *_):
        q.put(indata.copy())

    with sd.InputStream(samplerate=RATE, channels=CHANNELS, dtype="int16", callback=_cb):
        while not stop_evt.is_set():
            try:
                frames.append(q.get(timeout=0.1))
            except queue.Empty:
                pass

def _save_wav(frames) -> str | None:
    if not frames:
        return None
    pcm = np.concatenate(frames).tobytes()
    ts  = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(OUT_DIR, f"{ts}.wav")
    with wave.open(path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(pcm)
    return path

# ────────────────── UI utils ─────────────────────────

def _autoscroll(tag_suffix: str = "") -> None:
    """Auto‑scroll while user is at bottom; Esc or PageUp (keyCode 33) pauses it."""
    uid = uuid.uuid4().hex[:8] + tag_suffix
    st.components.v1.html(
        f"""
        <script id="asc_{uid}">
        (() => {{
          const win   = window.parent;
          const doc   = win.document;
          const root  = doc.querySelector('section.main');
          let paused  = false;

          const nearBottom = () => win.scrollY + win.innerHeight >= doc.documentElement.scrollHeight - 120;

          win.addEventListener('scroll',   () => paused = !nearBottom(), {{passive:true}});
          win.addEventListener('keydown',  (e) => {{
            if (e.key === 'Escape' || e.key === 'PageUp' || e.keyCode === 33) paused = true;
          }});

          const scrollDown = () => {{
            if (paused) return;
            const btm = doc.getElementById('chat_bottom');
            if (btm) btm.scrollIntoView({{behavior:'smooth', block:'end'}});
          }};

          if (nearBottom()) scrollDown();
          if (root) new MutationObserver(scrollDown).observe(root, {{childList:true, subtree:true}});
        }})();
        </script>
        """,
        height=0,
    )

# ────────────────── AI helpers ───────────────────────

def _transcribe(path: str) -> str:
    client = OpenAI()
    with open(path, "rb") as f:
        res = client.audio.transcriptions.create(model="whisper-1", file=f)
    return res.text


def _chat_stream(prompt: str) -> str:
    client = OpenAI()
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    holder = st.empty(); full = ""
    _autoscroll("init")

    stream = client.chat.completions.create(model="gpt-4o", messages=st.session_state.chat_history, stream=True)
    for chunk in stream:
        part = chunk.choices[0].delta.content
        if part:
            full += part
            holder.markdown(full + "▌<span id='chat_bottom'></span>", unsafe_allow_html=True)
            _autoscroll("run")

    holder.markdown(full + "<span id='chat_bottom'></span>", unsafe_allow_html=True)
    st.session_state.chat_history.append({"role": "assistant", "content": full})
    return full

# ────────────────── main UI ──────────────────────────

st.set_page_config("Voice Recorder + ChatGPT", "🎙️", layout="centered")
st.title("🎙️ Voice Recorder with ChatGPT")

rec, stop = st.columns(2)
with rec:
    if st.button("▶️ Start Recording", disabled=st.session_state.recording):
        st.session_state.audio_q  = queue.Queue()
        st.session_state.frames  = []
        st.session_state.stop_evt = threading.Event()
        threading.Thread(target=_recorder, args=(st.session_state.stop_evt, st.session_state.audio_q, st.session_state.frames), daemon=True).start()
        st.session_state.recording = True
        st.rerun()

with stop:
    if st.button("⏹️ Stop Recording", disabled=not st.session_state.recording):
        st.session_state.stop_evt.set()
        st.session_state.last_wav = _save_wav(st.session_state.frames)
        st.session_state.frames   = []
        st.session_state.recording = False
        st.rerun()

if st.session_state.recording:
    st.info("🔴 Recording…")

if st.session_state.last_wav:
    st.audio(open(st.session_state.last_wav, "rb").read(), format="audio/wav")
    if st.button("📝 Transcribe"):
        with st.spinner("Transcribing…"):
            st.session_state.transcription = _transcribe(st.session_state.last_wav)

if st.session_state.transcription:
    st.text_area("Transcription", value=st.session_state.transcription, height=160)
    if st.button("💬 Ask ChatGPT"):
        st.session_state.streaming = True
        st.rerun()

if st.session_state.streaming:
    with st.spinner("ChatGPT thinking…"):
        st.session_state.chat_response = _chat_stream(st.session_state.transcription)
    st.session_state.streaming = False
    st.rerun()

if st.session_state.chat_response:
    st.subheader("🤖 ChatGPT Response")
    st.markdown(st.session_state.chat_response + "<span id='chat_bottom'></span>", unsafe_allow_html=True)
    _autoscroll("done")
