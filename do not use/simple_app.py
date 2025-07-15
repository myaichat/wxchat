import streamlit as st
import os
from dotenv import load_dotenv
import openai
from include.transcribe import Transcribe
import speech_recognition as sr
import uuid
import threading
import time
import io
import wave

# Load environment variables
load_dotenv()

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI()

# Initialize session state
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = [
        {"role": "system", "content": """You are a chatbot that assists with Technical interview for Python developer. 
         numerate answer options globally with one sequence. Answer in english"""}
    ]

if 'transcriber' not in st.session_state:
    st.session_state.transcriber = Transcribe()

if 'is_recording' not in st.session_state:
    st.session_state.is_recording = False

if 'audio_data' not in st.session_state:
    st.session_state.audio_data = None

if 'recognizer' not in st.session_state:
    st.session_state.recognizer = sr.Recognizer()

if 'microphone' not in st.session_state:
    st.session_state.microphone = sr.Microphone()

if 'recording_thread' not in st.session_state:
    st.session_state.recording_thread = None

if 'recorded_audio' not in st.session_state:
    st.session_state.recorded_audio = None

if 'selected_model' not in st.session_state:
    st.session_state.selected_model = "gpt-4o"

if 'recording_start_time' not in st.session_state:
    st.session_state.recording_start_time = None

def record_audio_continuously():
    """Continuously record audio while is_recording is True"""
    try:
        import pyaudio
        
        # Audio recording parameters
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100
        
        # Initialize PyAudio
        p = pyaudio.PyAudio()
        
        # Open stream
        stream = p.open(format=FORMAT,
                       channels=CHANNELS,
                       rate=RATE,
                       input=True,
                       frames_per_buffer=CHUNK)
        
        audio_frames = []
        
        # Record audio while is_recording is True
        while st.session_state.is_recording:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                audio_frames.append(data)
            except Exception:
                break
        
        # Stop and close the stream
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        # Convert to WAV format
        if audio_frames:
            # Create WAV file in memory
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(CHANNELS)
                wav_file.setsampwidth(p.get_sample_size(FORMAT))
                wav_file.setframerate(RATE)
                wav_file.writeframes(b''.join(audio_frames))
            
            st.session_state.recorded_audio = wav_buffer.getvalue()
        else:
            st.session_state.recorded_audio = None
            
    except ImportError:
        # Fallback to speech_recognition if pyaudio is not available
        try:
            with st.session_state.microphone as source:
                st.session_state.recognizer.adjust_for_ambient_noise(source, duration=0.2)
                
            audio_frames = []
            with st.session_state.microphone as source:
                while st.session_state.is_recording:
                    try:
                        # Record in small chunks
                        audio_chunk = st.session_state.recognizer.listen(source, timeout=0.1, phrase_time_limit=0.5)
                        audio_frames.append(audio_chunk.get_wav_data())
                    except sr.WaitTimeoutError:
                        continue
                    except Exception:
                        break
            
            # Combine all audio chunks
            if audio_frames:
                combined_audio = b''.join(audio_frames)
                st.session_state.recorded_audio = combined_audio
            else:
                st.session_state.recorded_audio = None
                
        except Exception as e:
            st.session_state.recorded_audio = None
    except Exception as e:
        st.session_state.recorded_audio = None

def start_recording():
    """Start recording audio in a separate thread"""
    if not st.session_state.is_recording:
        st.session_state.is_recording = True
        st.session_state.recorded_audio = None
        st.session_state.recording_start_time = time.time()
        
        # Start recording in a separate thread
        st.session_state.recording_thread = threading.Thread(target=record_audio_continuously)
        st.session_state.recording_thread.daemon = True
        st.session_state.recording_thread.start()

def stop_recording_and_process():
    """Stop recording and process the audio"""
    if st.session_state.is_recording:
        st.session_state.is_recording = False
        st.session_state.recording_start_time = None
        
        # Wait for recording thread to finish
        if st.session_state.recording_thread:
            st.session_state.recording_thread.join(timeout=2.0)
        
        # Process the recorded audio
        if st.session_state.recorded_audio:
            try:
                # Save audio to file
                audio_path = 'user_speech/'
                if not os.path.isdir(audio_path):
                    os.makedirs(audio_path)
                
                file_path = f'{audio_path}{uuid.uuid4()}-audio.wav'
                with open(file_path, 'wb') as f:
                    f.write(st.session_state.recorded_audio)
                
                return file_path
            except Exception as e:
                st.error(f"Error saving audio: {str(e)}")
                return None
        else:
            st.error("No audio recorded")
            return None
    return None

def get_chatgpt_response(prompt):
    """Get streaming response from ChatGPT"""
    try:
        st.session_state.conversation_history.append({"role": "user", "content": prompt})
        
        # Create a placeholder for streaming response
        response_placeholder = st.empty()
        full_response = ""
        
        # Stream the response
        stream = client.chat.completions.create(
            model=st.session_state.selected_model,
            messages=st.session_state.conversation_history,
            stream=True
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                full_response += chunk.choices[0].delta.content
                response_placeholder.markdown(full_response + "▌")
        
        # Remove the cursor and show final response
        response_placeholder.markdown(full_response)
        
        # Add the complete response to conversation history
        st.session_state.conversation_history.append({"role": "assistant", "content": full_response})
        
        return full_response
    except Exception as e:
        st.error(f"ChatGPT API error: {str(e)}")
        return None

def main():
    st.title("🎤 Voice Interview Copilot")
    st.markdown("**Click 'Start Recording' to begin, then 'Stop Recording' when done.**")
    
    # Model selection dropdown
    available_models = [
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k"
    ]
    
    st.session_state.selected_model = st.selectbox(
        "🤖 Select OpenAI Model:",
        available_models,
        index=available_models.index(st.session_state.selected_model) if st.session_state.selected_model in available_models else 0,
        help="Choose the OpenAI model for generating responses"
    )
    
    st.markdown("---")
    
    # Create columns for layout - center the push-to-talk button
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Create two buttons for start/stop recording
        col_start, col_stop = st.columns(2)
        
        with col_start:
            if st.button("🎤 Start Recording", key="start_btn", type="primary", disabled=st.session_state.is_recording):
                if not st.session_state.is_recording:
                    st.session_state.is_recording = True
                    st.session_state.recording_start_time = time.time()
                    st.session_state.recorded_audio = None
                    
                    # Start recording in a separate thread using speech_recognition
                    def record_with_sr():
                        try:
                            recognizer = sr.Recognizer()
                            microphone = sr.Microphone()
                            
                            with microphone as source:
                                recognizer.adjust_for_ambient_noise(source, duration=0.2)
                            
                            audio_chunks = []
                            with microphone as source:
                                while st.session_state.is_recording:
                                    try:
                                        # Record in small chunks while recording is active
                                        audio_chunk = recognizer.listen(source, timeout=0.5, phrase_time_limit=1.0)
                                        if st.session_state.is_recording:  # Check again in case it was stopped
                                            audio_chunks.append(audio_chunk.get_wav_data())
                                    except sr.WaitTimeoutError:
                                        continue
                                    except Exception:
                                        break
                            
                            # Combine all audio chunks
                            if audio_chunks:
                                st.session_state.recorded_audio = b''.join(audio_chunks)
                            else:
                                st.session_state.recorded_audio = None
                                
                        except Exception as e:
                            st.session_state.recorded_audio = None
                    
                    st.session_state.recording_thread = threading.Thread(target=record_with_sr)
                    st.session_state.recording_thread.daemon = True
                    st.session_state.recording_thread.start()
                    
                    st.success("🎙️ Recording started! Click 'Stop Recording' when done.")
        
        with col_stop:
            if st.button("⏹️ Stop Recording", key="stop_btn", type="secondary", disabled=not st.session_state.is_recording):
                if st.session_state.is_recording:
                    st.session_state.is_recording = False
                    st.session_state.recording_start_time = None
                    
                    # Wait for recording thread to finish
                    if st.session_state.recording_thread:
                        st.session_state.recording_thread.join(timeout=2.0)
                    
                    # Process the recorded audio
                    if st.session_state.recorded_audio:
                        try:
                            # Save audio to file
                            audio_path = 'user_speech/'
                            if not os.path.isdir(audio_path):
                                os.makedirs(audio_path)
                            
                            file_path = f'{audio_path}{uuid.uuid4()}-audio.wav'
                            with open(file_path, 'wb') as f:
                                f.write(st.session_state.recorded_audio)
                            
                            st.success("✅ Recording completed!")
                            
                            with st.spinner("📝 Transcribing audio..."):
                                try:
                                    # Transcribe the audio
                                    transcript = st.session_state.transcriber.transcribe_audio(file_path)
                                except Exception as e:
                                    st.error(f"Transcription error: {str(e)}")
                                    transcript = None
                            
                            # Clean up audio file
                            try:
                                os.remove(file_path)
                            except:
                                pass
                            
                            # Store transcript in session state for display
                            if transcript and transcript.strip():
                                st.session_state.last_transcript = transcript.strip()
                                st.rerun()
                            else:
                                st.error("No transcript generated or transcript is empty")
                                
                        except Exception as e:
                            st.error(f"Error saving audio: {str(e)}")
                    else:
                        st.error("No audio recorded")
        
        # Show recording status with progress bar
        if st.session_state.is_recording and st.session_state.recording_start_time:
            # Calculate elapsed time
            elapsed_time = time.time() - st.session_state.recording_start_time
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)
            
            # Create progress bar container
            progress_container = st.container()
            with progress_container:
                st.markdown("🔴 **Recording in progress...**")
                
                # Show elapsed time
                time_display = f"⏱️ {minutes:02d}:{seconds:02d}"
                st.markdown(f"**{time_display}**")
                
                # Create animated progress bar (cycles every 2 seconds)
                progress_value = (elapsed_time % 2) / 2
                progress_bar = st.progress(progress_value)
                
                # Auto-refresh every 0.1 seconds to update the timer and progress bar
                time.sleep(0.1)
                st.rerun()
        
    
    # Display transcript and response outside of columns for full width
    if hasattr(st.session_state, 'last_transcript') and st.session_state.last_transcript:
        st.markdown("### 📝 Your Question:")
        st.info(st.session_state.last_transcript)
        
        st.markdown("### 🤖 ChatGPT Response:")
        response = get_chatgpt_response(st.session_state.last_transcript)
        
        # Clear the transcript after processing
        st.session_state.last_transcript = None
    
    # Display conversation history
    if len(st.session_state.conversation_history) > 1:  # Skip system message
        st.markdown("---")
        st.markdown("### 💬 Conversation History")
        
        for i, message in enumerate(st.session_state.conversation_history[1:], 1):  # Skip system message
            if message["role"] == "user":
                st.markdown(f"**Q{i//2 + 1}:** {message['content']}")
            elif message["role"] == "assistant":
                st.markdown(f"**A{i//2 + 1}:** {message['content']}")
                st.markdown("---")
    
    # Clear conversation button
    if st.button("🗑️ Clear Conversation"):
        st.session_state.conversation_history = [
            {"role": "system", "content": """You are a chatbot that assists with Technical interview for Python developer. 
             numerate answer options globally with one sequence. Answer in english"""}
        ]
        st.success("Conversation cleared!")
        st.rerun()

if __name__ == "__main__":
    main()
