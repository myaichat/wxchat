# Voice Interview Copilot - Streamlit App

A Streamlit-based voice interview assistant that allows you to record questions, transcribe them using OpenAI Whisper, and get responses from ChatGPT.

## Features

- 🎤 **Voice Recording**: Click and hold to record your questions
- 📝 **Speech Transcription**: Uses OpenAI Whisper for accurate transcription
- 🤖 **ChatGPT Integration**: Get intelligent responses to your technical interview questions
- 💬 **Conversation History**: View your entire conversation history
- 🗑️ **Clear Conversation**: Reset the conversation at any time

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements-streamlit.txt
   ```

2. **Environment Variables**:
   Create a `.env` file in the project root with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

3. **Run the App**:
   ```bash
   streamlit run app.py
   ```

## Usage

1. Open the app in your browser (usually http://localhost:8501)
2. Click "🔴 Hold to Record" to start recording your question
3. Click "⏹️ Stop Recording" when you're done speaking
4. Wait for the transcription and ChatGPT response
5. View your conversation history below
6. Use "🗑️ Clear Conversation" to start fresh

## Requirements

- Python 3.7+
- Microphone access
- OpenAI API key
- Internet connection

## Technical Details

The app uses:
- **Streamlit** for the web interface
- **SpeechRecognition** library for audio capture
- **OpenAI Whisper** for speech-to-text transcription
- **OpenAI GPT-4** for generating responses
- **Threading** for non-blocking audio recording

## Troubleshooting

- **Microphone Issues**: Ensure your microphone is working and permissions are granted
- **API Errors**: Check your OpenAI API key and account credits
- **Audio Quality**: Speak clearly and ensure minimal background noise
- **Recording Problems**: Try refreshing the page if recording gets stuck
