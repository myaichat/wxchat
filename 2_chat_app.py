# chat_app_concurrent_stream.py – Streamlit mic‑recorder with true dual streaming
# -----------------------------------------------------------------------------
# Key differences from the previous version
# 1.  The *Web UI* and *API* answers are streamed **concurrently** in two daemon
#     threads instead of sequentially. Each thread writes to a fixed placeholder
#     so subsequent script reruns do not override the widgets the user sees.
# 2.  We remove the old separate Web‑UI / API handlers and replace them with a
#     single dual‑stream handler that fires once, flips the flags to False,
#     launches both background threads, and immediately stops the current run
#     with `st.stop()` to keep the UI responsive.
# -----------------------------------------------------------------------------

import streamlit as st
import sounddevice as sd
import numpy as np
import wave, os, io, queue, threading, datetime, json, requests
from pathlib import Path
from dotenv import load_dotenv
from streamlit.runtime.scriptrunner import add_script_run_ctx
from include.transcribe import Transcribe

# ─────────────────────── constants ───────────────────────
RATE, CH = 16_000, 1
OUT_DIR  = "recordings"
BACKEND_URL = "http://localhost:8002/ask-chatgpt"
TIMEOUT_SEC = 60
LOGS_DIR = "logs"
os.makedirs(OUT_DIR,  exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
load_dotenv(dotenv_path=Path(".") / ".env", override=True)

# ─────────────────────── session state defaults ───────────────────────
ss = st.session_state
_defaults = {
    "recording": False,
    "last_wav": None,
    "transcription": None,
    "transcribing": False,
    "transcriber": None,
    "auto_transcribe": True,
    "conversation_history": [],
    "chatgpt_response": None,
    "generating_response": False,   # Web UI flag
    "api_response": None,
    "generating_api_response": False,  # API flag
    "selected_model": "gpt-4o",
    "auto_chatgpt": True,
    "stop_streaming": False,
    "manual_transcription": None,
}
for k, v in _defaults.items():
    if k not in ss:
        ss[k] = v

# unique log‑file per session
if "session_log_file" not in ss:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ss.session_log_file = os.path.join(LOGS_DIR, f"chat_session_{ts}.json")

# fixed placeholders – created once and reused every rerun
if "web_plh" not in ss:
    ss.web_plh = st.empty()
if "api_plh" not in ss:
    ss.api_plh = st.empty()

# ─────────────────────── helper utilities ───────────────────────

def start_thread(fn, *args, **kwargs):
    """Start a daemon thread that is allowed to call Streamlit APIs."""
    th = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    add_script_run_ctx(th)
    th.start()
    return th


def record_worker(stop_evt: threading.Event, audio_q: queue.Queue, frames: list[np.ndarray]):
    """Background audio recorder that never touches Streamlit objects."""
    def _cb(indata, *_):
        audio_q.put(indata.copy())

    with sd.InputStream(samplerate=RATE, channels=CH, dtype="int16", callback=_cb):
        while not stop_evt.is_set():
            try:
                frames.append(audio_q.get(timeout=0.1))
            except queue.Empty:
                pass


def save_wav(frames) -> str | None:
    if not frames:
        return None
    pcm = np.concatenate(frames).tobytes()
    path = os.path.join(OUT_DIR, f"{datetime.datetime.now():%Y%m%d-%H%M%S}.wav")
    with wave.open(path, "wb") as wf:
        wf.setnchannels(CH)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(pcm)
    return path


def transcribe_audio_file(path: str) -> str | None:
    try:
        if ss.transcriber is None:
            ss.transcriber = Transcribe()
        return ss.transcriber.transcribe_audio(path)
    except Exception as e:
        st.error(f"Transcription failed: {e}")
        return None


def current_transcription() -> str | None:
    return ss.get("transcription_display", ss.transcription)


def log_qa_pair(q: str, a: str):
    try:
        with open(ss.session_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": datetime.datetime.now().isoformat(),
                "question": q,
                "answer": a,
                "model": ss.selected_model,
            }, ensure_ascii=False) + "\n")
    except Exception as e:
        st.error(f"Failed to write log: {e}")

# --- OpenAI direct ------------------------------------------------------

def get_chatgpt_response(prompt: str, *, container, history):
    from openai import OpenAI
    client = OpenAI()

    response_plh = container.empty()
    full_resp = ""
    for chunk in client.chat.completions.create(
        model=ss.selected_model,
        messages=history + [{"role": "user", "content": prompt}],
        stream=True,
    ):
        if ss.stop_streaming:
            break
        delta = chunk.choices[0].delta.content or ""
        if delta:
            full_resp += delta
            response_plh.markdown(full_resp + "▌")
    response_plh.markdown(full_resp)
    return full_resp

# --- backend proxy ------------------------------------------------------

def get_backend_response(prompt: str, *, container, history):
    payload = {"message": prompt + ". Answer in clean raw markdown without citations.", "timeout": TIMEOUT_SEC}
    response_plh = container.empty()
    txt = ""
    with requests.post(BACKEND_URL, json=payload, stream=True) as r:
        r.raise_for_status()
        for raw in r.iter_lines(decode_unicode=True):
            if ss.stop_streaming:
                break
            if not raw:
                continue
            data = json.loads(raw)
            if data["status"] == "streaming":
                chunk = data["content"]
                txt += chunk[len(txt):]
                response_plh.markdown(txt + "▌")
            elif data["status"] == "complete":
                txt = data["content"]
                response_plh.markdown(txt)
                break
    return txt

# ─────────────────────── UI – header & model picker ───────────────────────
col_title, col_model = st.columns([4, 1])
with col_title:
    st.title("🎙️ SpeakStream AI")
with col_model:
    ss.selected_model = st.selectbox(
        "Model", [
            "gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini",
            "gpt-3.5-turbo", "gpt-3.5-turbo-16k",
        ], index=2
    )

# ---------- settings ----------
left, right = st.columns(2)
with left:
    ss.auto_transcribe = st.checkbox("🤖 Auto‑transcribe", value=ss.auto_transcribe)
with right:
    ss.auto_chatgpt = st.checkbox("🤖 Auto ChatGPT", value=ss.auto_chatgpt)

# ────────── record toggle ──────────
label = "▶️ Start" if not ss.recording else "⏹️ Stop"
if st.button(label, key="rec_toggle"):
    if not ss.recording:
        # start recording
        ss.recording = True
        ss.transcription = None
        ss.chatgpt_response = ss.api_response = None
        ss.generating_response = ss.generating_api_response = False
        q, frames, stop_evt = queue.Queue(), [], threading.Event()
        ss.curr_audio_q, ss.curr_frames, ss.curr_stop_evt = q, frames, stop_evt
        start_thread(record_worker, stop_evt, q, frames)  # recorder thread
        st.success("Recording…")
        st.rerun()
    else:
        # stop recording
        ss.recording = False
        ss.curr_stop_evt.set()
        threading.Event().wait(0.3)
        wav_path = save_wav(ss.curr_frames)
        ss.curr_frames.clear()
        if wav_path:
            st.success(f"Saved: **{wav_path}**")
            ss.last_wav = wav_path
            if ss.auto_transcribe:
                ss.transcribing = True
                st.rerun()
        else:
            st.error("No audio captured")
        st.rerun()

# ---------- playback ----------
if ss.last_wav:
    st.audio(open(ss.last_wav, "rb").read(), format="audio/wav")

# ---------- transcription ----------
if ss.last_wav and not ss.recording:
    col_t, col_s = st.columns([1, 2])
    with col_t:
        if st.button("📝 Transcribe", disabled=ss.transcribing):
            ss.transcribing = True
            st.rerun()
    with col_s:
        if ss.transcribing:
            st.info("🔄 Transcribing…")
        elif ss.transcription:
            st.success("✅ Done")

    if ss.transcribing:
        txt = transcribe_audio_file(ss.last_wav)
        ss.transcription, ss.transcribing = txt, False
        if txt and ss.auto_chatgpt:
            ss.generating_response = ss.generating_api_response = True
        st.rerun()

    if ss.transcription:
        with st.form("tx_form"):
            st.subheader("📄 Transcription")
            edited = st.text_area("", value=current_transcription(), height=100, key="transcription_display")
            ok = st.form_submit_button("💬 Get ChatGPT Response (Ctrl+Enter)")
        if ok:
            ss.manual_transcription = edited
            ss.generating_response = ss.generating_api_response = True
            st.rerun()

# ---------- chatGPT response section ----------
if ss.transcription and not ss.recording:
    st.subheader("🤖 ChatGPT Response")

    cols = st.columns(2)
    with cols[0]:
        st.markdown("### Web UI")
        # actual placeholder is ss.web_plh – nothing else to do
    with cols[1]:
        st.markdown("### API")
        # actual placeholder is ss.api_plh
        if st.button("🔄 Get API Response"):
            ss.generating_response = ss.generating_api_response = True
            ss.stop_streaming = False
            ss.chatgpt_response = ss.api_response = None
            st.rerun()

# ---------- dual‑stream handler ----------
if (ss.generating_response or ss.generating_api_response) and not ss.stop_streaming:
    question = current_transcription() or ""
    history_copy = ss.conversation_history.copy()

    def t_web():
        resp = get_backend_response(question, container=ss.web_plh, history=history_copy)
        if resp:
            ss.chatgpt_response = resp
            log_qa_pair(question, resp)

    def t_api():
        resp = get_chatgpt_response(question, container=ss.api_plh, history=history_copy)
        if resp:
            ss.api_response = resp

    if ss.generating_response:
        start_thread(t_web)
    if ss.generating_api_response:
        start_thread(t_api)

    # Prevent the next rerun from re‑entering this block
    ss.generating_response = ss.generating_api_response = False
    st.stop()

# ---------- handle stop streaming ----------
if ss.stop_streaming:
    ss.stop_streaming = False
    ss.generating_response = ss.generating_api_response = False
    ss.manual_transcription = None
    st.info("🛑 Streaming stopped by user")

# live status
if ss.recording:
    st.markdown("🔴 **Recording…** Press Stop when done.")
