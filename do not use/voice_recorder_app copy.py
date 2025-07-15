# voice_recorder_app.py  –  thread‑safe Streamlit mic recorder
import streamlit as st
import sounddevice as sd
import numpy as np
import wave, os, io, queue, threading, datetime
from include.transcribe import Transcribe

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

# ───────────────────────── UI ───────────────────────────────
st.title("🎙️ Simple Voice Recorder")

# ---------- Settings ----------
st.session_state.auto_transcribe = st.checkbox("🤖 Auto-transcribe after recording", 
                                               value=st.session_state.auto_transcribe)

col_start, col_stop = st.columns(2)

# ---------- Start ----------
with col_start:
    if st.button("▶️ Start", disabled=st.session_state.recording):
        st.session_state.recording = True
        # Clear previous transcription when starting new recording
        st.session_state.transcription = None
        st.session_state.transcribing = False

        # independent objects for this recording session
        audio_q   = queue.Queue()
        frames    = []
        stop_evt  = threading.Event()

        # keep refs so we can access them when stopping
        st.session_state.curr_audio_q  = audio_q
        st.session_state.curr_frames   = frames
        st.session_state.curr_stop_evt = stop_evt

        threading.Thread(target=record_worker,
                         args=(stop_evt, audio_q, frames),
                         daemon=True).start()
        st.success("Recording…")

# ---------- Stop ----------
with col_stop:
    if st.button("⏹️ Stop", disabled=not st.session_state.recording):
        st.session_state.recording = False
        st.session_state.curr_stop_evt.set()

        # give worker a moment to flush
        threading.Event().wait(0.3)

        wav_path = save_wav(st.session_state.curr_frames)
        st.session_state.last_wav = wav_path
        st.session_state.curr_frames.clear()

        if wav_path:
            st.success(f"Saved: **{wav_path}**")
            
            # Auto-transcribe if enabled
            if st.session_state.auto_transcribe:
                st.session_state.transcribing = True
                st.session_state.transcription = None
                st.rerun()  # Force UI refresh to show transcribing state
        else:
            st.error("No audio captured")

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

    # Display transcription result
    if st.session_state.transcription:
        st.subheader("📄 Transcription")
        st.text_area("Transcribed Text:", 
                    value=st.session_state.transcription, 
                    height=150, 
                    disabled=False,
                    key="transcription_display")

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
        st.rerun()  # Refresh to show results

# live status
if st.session_state.recording:
    st.markdown("🔴 **Recording...** Press Stop when done.")
