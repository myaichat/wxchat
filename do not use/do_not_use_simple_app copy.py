import streamlit as st
import os
from dotenv import load_dotenv
import openai
from include.transcribe import Transcribe
from push_to_talk_component import push_to_talk_button
import speech_recognition as sr
import uuid
import threading
import time

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

def record_audio_continuously():
    """Continuously record audio while is_recording is True"""
    try:
        with st.session_state.microphone as source:
            st.session_state.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
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
        
    except Exception as e:
        st.session_state.recorded_audio = None

def start_recording():
    """Start recording audio in a separate thread"""
    if not st.session_state.is_recording:
        st.session_state.is_recording = True
        st.session_state.recorded_audio = None
        
        # Start recording in a separate thread
        st.session_state.recording_thread = threading.Thread(target=record_audio_continuously)
        st.session_state.recording_thread.daemon = True
        st.session_state.recording_thread.start()

def stop_recording_and_process():
    """Stop recording and process the audio"""
    if st.session_state.is_recording:
        st.session_state.is_recording = False
        
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
    """Get response from ChatGPT"""
    try:
        st.session_state.conversation_history.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=st.session_state.selected_model,
            messages=st.session_state.conversation_history,
            stream=False
        )
        
        assistant_response = response.choices[0].message.content
        st.session_state.conversation_history.append({"role": "assistant", "content": assistant_response})
        
        return assistant_response
    except Exception as e:
        st.error(f"ChatGPT API error: {str(e)}")
        return None

def main():
    st.title("🎤 Voice Interview Copilot")
    st.markdown("**Hold the button to record your question, then get transcription and ChatGPT response.**")
    
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
    
    # Create columns for layout
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Use a simple button for now to test functionality
        if st.button("🎤 Record Question", key="record_btn", type="primary"):
            with st.spinner("🎙️ Recording... Speak now!"):
                # Record audio using the existing transcribe module
                file_path = st.session_state.transcriber.record_audio()
            
            st.success("✅ Recording completed!")
            
            with st.spinner("📝 Transcribing audio..."):
                # Transcribe the audio
                transcript = st.session_state.transcriber.transcribe_audio(file_path)
            
            if transcript:
                st.markdown("### 📝 Your Question:")
                st.info(transcript)
                
                with st.spinner("🤖 Getting ChatGPT response..."):
                    response = get_chatgpt_response(transcript)
                
                if response:
                    st.markdown("### 🤖 ChatGPT Response:")
                    st.markdown(response)
            else:
                st.error("❌ Could not transcribe audio. Please try again.")
            
            # Clean up audio file
            try:
                os.remove(file_path)
            except:
                pass
    
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
