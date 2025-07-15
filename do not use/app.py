import streamlit as st
import os
import sys
import time
import threading
import queue
from dotenv import load_dotenv
import openai
from include.voice import Voice
from include.transcribe import Transcribe
import speech_recognition as sr
import uuid
# from push_to_talk_component import push_to_talk_button

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

if 'is_recording' not in st.session_state:
    st.session_state.is_recording = False

if 'transcriber' not in st.session_state:
    st.session_state.transcriber = Transcribe()

if 'voice' not in st.session_state:
    st.session_state.voice = Voice()

if 'audio_queue' not in st.session_state:
    st.session_state.audio_queue = queue.Queue()

if 'recording_thread' not in st.session_state:
    st.session_state.recording_thread = None

class StreamlitTranscribe:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.audio_path = 'user_speech/'
        if not os.path.isdir(self.audio_path):
            os.makedirs(self.audio_path)
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.is_recording = False
        
        # Try to initialize microphone with error handling
        try:
            self.microphone = sr.Microphone()
        except OSError as e:
            st.error(f"Microphone initialization failed: {str(e)}")
            st.error("Please ensure you have a microphone connected and accessible.")
            self.microphone = None
        
    def start_recording(self):
        """Start recording audio in a separate thread"""
        self.is_recording = True
        
        def record():
            try:
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                audio_data = None
                with self.microphone as source:
                    # Record until stopped
                    audio_data = self.recognizer.listen(source, timeout=None, phrase_time_limit=None)
                
                if audio_data and self.is_recording:
                    # Save audio file
                    file_path = f'{self.audio_path}{uuid.uuid4()}-audio.wav'
                    with open(file_path, 'wb') as f:
                        f.write(audio_data.get_wav_data())
                    
                    # Add to queue for processing
                    st.session_state.audio_queue.put(file_path)
                    
            except Exception as e:
                st.error(f"Recording error: {str(e)}")
        
        # Start recording in a separate thread
        thread = threading.Thread(target=record)
        thread.daemon = True
        thread.start()
        return thread
    
    def stop_recording(self):
        """Stop recording"""
        self.is_recording = False
    
    def transcribe_audio(self, audio_file_path):
        """Transcribe audio file using OpenAI Whisper"""
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            return transcript
        except Exception as e:
            st.error(f"Transcription error: {str(e)}")
            return None

def get_chatgpt_response(prompt):
    """Get response from ChatGPT"""
    try:
        st.session_state.conversation_history.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model="gpt-4",
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
    st.markdown("**Click to start recording, click again to stop and process your question.**")
    
    # Initialize transcriber if not exists
    if 'streamlit_transcriber' not in st.session_state:
        st.session_state.streamlit_transcriber = StreamlitTranscribe()
    
    # Check if microphone is available
    if st.session_state.streamlit_transcriber.microphone is None:
        st.error("❌ Microphone not available. Please connect a microphone and refresh the page.")
        return
    
    # Create columns for layout
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Toggle recording button
        if st.session_state.is_recording:
            button_text = "⏹️ Stop Recording"
            button_color = "secondary"
        else:
            button_text = "🔴 Start Recording"
            button_color = "primary"
        
        if st.button(button_text, key="record_toggle_btn", type=button_color):
            if not st.session_state.is_recording:
                # Start recording
                st.session_state.is_recording = True
                st.session_state.recording_thread = st.session_state.streamlit_transcriber.start_recording()
                st.rerun()
            else:
                # Stop recording
                st.session_state.is_recording = False
                st.session_state.streamlit_transcriber.stop_recording()
                st.rerun()
    
    # Status indicator
    if st.session_state.is_recording:
        st.markdown("### 🔴 Recording in progress...")
        st.markdown("Click 'Stop Recording' when you're done speaking.")
    
    # Process audio queue
    if not st.session_state.audio_queue.empty():
        audio_file_path = st.session_state.audio_queue.get()
        
        with st.spinner("Transcribing audio..."):
            transcript = st.session_state.streamlit_transcriber.transcribe_audio(audio_file_path)
        
        if transcript:
            st.markdown("### 📝 Your Question:")
            st.info(transcript)
            
            with st.spinner("Getting response from ChatGPT..."):
                response = get_chatgpt_response(transcript)
            
            if response:
                st.markdown("### 🤖 ChatGPT Response:")
                st.markdown(response)
        
        # Clean up audio file
        try:
            os.remove(audio_file_path)
        except:
            pass
    
    # Display conversation history
    if len(st.session_state.conversation_history) > 1:  # Skip system message
        st.markdown("### 💬 Conversation History")
        
        for i, message in enumerate(st.session_state.conversation_history[1:], 1):  # Skip system message
            if message["role"] == "user":
                st.markdown(f"**You ({i//2 + 1}):** {message['content']}")
            elif message["role"] == "assistant":
                st.markdown(f"**Assistant ({i//2 + 1}):** {message['content']}")
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
