import streamlit as st
import asyncio
import sounddevice as sd
import numpy as np
import wave
import os
import queue
import threading
import datetime
from streaming_chat import send_message_with_streaming

# Audio recording constants
RATE, CH = 16_000, 1
OUT_DIR = "recordings"
os.makedirs(OUT_DIR, exist_ok=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "streaming_response" not in st.session_state:
    st.session_state.streaming_response = ""
if "is_streaming" not in st.session_state:
    st.session_state.is_streaming = False

# Recording session state
if "recording" not in st.session_state:
    st.session_state.recording = False
if "last_wav" not in st.session_state:
    st.session_state.last_wav = None

# Recording helper functions
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

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(OUT_DIR, f"{ts}.wav")
    with wave.open(path, "wb") as wf:
        wf.setnchannels(CH)
        wf.setsampwidth(2)     # int16
        wf.setframerate(RATE)
        wf.writeframes(pcm)
    return path

st.title("🚀 Streaming Chat Test with Voice Recording")
st.write("Test the streaming chat functionality")

# Recording Section
st.subheader("🎙️ Voice Recording")

# Start/Stop recording button
label = "▶️ Start Recording" if not st.session_state.recording else "⏹️ Stop Recording"

if st.button(label, key="rec_toggle"):
    if not st.session_state.recording:          # START branch
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
            daemon=True
        ).start()

        st.success("🔴 Recording...")
        st.rerun()

    else:                                     # STOP branch
        st.session_state.recording = False
        st.session_state.curr_stop_evt.set()
        threading.Event().wait(0.3)           # let buffer flush

        wav_path = save_wav(st.session_state.curr_frames)
        st.session_state.last_wav = wav_path
        st.session_state.curr_frames.clear()

        if wav_path:
            st.success(f"✅ Saved: **{wav_path}**")
        else:
            st.error("❌ No audio captured")

        st.rerun()

# Show recording status
if st.session_state.recording:
    st.markdown("🔴 **Recording...** Press Stop when done.")

# Audio playback
if st.session_state.last_wav:
    st.subheader("🔊 Playback")
    st.audio(open(st.session_state.last_wav, "rb").read(), format="audio/wav")

st.divider()

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Input form
with st.form("chat_form", clear_on_submit=True):
    question = st.text_input("Enter your question:", placeholder="Ask me anything...")
    submitted = st.form_submit_button("Send", disabled=st.session_state.is_streaming)

# Handle form submission
if submitted and question and not st.session_state.is_streaming:
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": question})
    
    # Set streaming state
    st.session_state.is_streaming = True
    st.session_state.streaming_response = ""
    
    # Display user message
    with st.chat_message("user"):
        st.write(question)
    
    # Create placeholder for streaming response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        
        # Stream the response
        async def stream_response():
            full_response = ""
            try:
                async for response in send_message_with_streaming(question, timeout=60):
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
        try:
            final_response = asyncio.run(stream_response())
            
            # Add assistant response to chat history
            if final_response:
                st.session_state.messages.append({"role": "assistant", "content": final_response})
                
        except Exception as e:
            error_msg = f"❌ Failed to process request: {str(e)}"
            response_placeholder.markdown(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
        
        finally:
            # Reset streaming state
            st.session_state.is_streaming = False
            st.rerun()

# Show streaming status
if st.session_state.is_streaming:
    st.info("🔄 Streaming response...")

# Clear chat button
if st.button("Clear Chat"):
    st.session_state.messages = []
    st.session_state.streaming_response = ""
    st.session_state.is_streaming = False
    st.rerun()

# Debug info
with st.expander("Debug Info"):
    st.write("**Session State:**")
    st.json({
        "messages_count": len(st.session_state.messages),
        "is_streaming": st.session_state.is_streaming,
        "streaming_response_length": len(st.session_state.streaming_response),
        "recording": st.session_state.recording,
        "last_wav": st.session_state.last_wav
    })
