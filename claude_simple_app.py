import streamlit as st
import threading
import time
from streamlit.runtime.scriptrunner import add_script_run_ctx

# Configure page layout
st.set_page_config(
    page_title="Claude Web UI Simple",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Import Claude handler functions
from chat_handlers.claude_handler import (
    start_concurrent_streaming as claude_start_concurrent_streaming,
    render_claude_responses,
    handle_concurrent_streaming as claude_handle_concurrent_streaming,
    handle_stopped_streaming as claude_handle_stopped_streaming
)

# Custom CSS
st.markdown("""
<style>
.main-header {
    font-size: 32px;
    font-weight: 600;
    color: #4f46e5;
    margin-bottom: 20px;
    text-align: center;
}
.box-header {
    font-size: 26px;
    font-weight: 550;
    color: #4f46e5;
    margin-bottom: 6px;
    margin-left: 0px;
    text-transform: uppercase;
    letter-spacing: 1px;
}
</style>
""", unsafe_allow_html=True)

# Initialize Claude-specific session state variables
if "claude_conversation_history" not in st.session_state:
    st.session_state.claude_conversation_history = []
if "claude_api_conversation_history" not in st.session_state:
    st.session_state.claude_api_conversation_history = []
if "claude_response" not in st.session_state:
    st.session_state.claude_response = None
if "claude_api_response" not in st.session_state:
    st.session_state.claude_api_response = None
if "claude_webui_streaming_text" not in st.session_state:
    st.session_state.claude_webui_streaming_text = ""
if "claude_api_streaming_text" not in st.session_state:
    st.session_state.claude_api_streaming_text = ""
if "claude_webui_stream_complete" not in st.session_state:
    st.session_state.claude_webui_stream_complete = False
if "claude_api_stream_complete" not in st.session_state:
    st.session_state.claude_api_stream_complete = False
if "claude_concurrent_streaming_active" not in st.session_state:
    st.session_state.claude_concurrent_streaming_active = False
if "claude_generating_response" not in st.session_state:
    st.session_state.claude_generating_response = False
if "claude_generating_api_response" not in st.session_state:
    st.session_state.claude_generating_api_response = False
if "claude_pending_log_question" not in st.session_state:
    st.session_state.claude_pending_log_question = None
if "claude_pending_log_webui_question" not in st.session_state:
    st.session_state.claude_pending_log_webui_question = None
if "claude_pending_log_api_question" not in st.session_state:
    st.session_state.claude_pending_log_api_question = None
if "stop_streaming" not in st.session_state:
    st.session_state.stop_streaming = False
if "selected_model" not in st.session_state:
    st.session_state.selected_model = "claude-3-5-sonnet-20241022"
if "session_log_file" not in st.session_state:
    import datetime
    import os
    LOGS_DIR = "logs"
    os.makedirs(LOGS_DIR, exist_ok=True)
    session_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.session_log_file = os.path.join(LOGS_DIR, f"claude_session_{session_timestamp}.json")

# Additional session state variables required by render_claude_responses()
if "transcription" not in st.session_state:
    st.session_state.transcription = None
if "recording" not in st.session_state:
    st.session_state.recording = False

# Main UI
st.markdown('<div class="main-header">🤖 Claude Web UI Simple</div>', unsafe_allow_html=True)

# Instructions
st.markdown("""
### Prerequisites
1. **Start Chrome with debug mode:**
   ```bash
   chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
   ```
   Or use: `start_chrome_for_claude.bat`

2. **Open Claude.ai** in Chrome and log in

3. **Enter your question** below and click Send

### Note
- Web UI mode requires Chrome debug mode (may show connection errors in Streamlit)
- API mode requires `ANTHROPIC_API_KEY` in .env file
- Both modes will be attempted simultaneously
""")

# Question input
st.subheader("💬 Ask Claude")
question = st.text_area(
    "Enter your question:",
    height=100,
    placeholder="Type your question here...",
    key="question_input"
)

# Control buttons
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    send_button = st.button(
        "🚀 Send to Claude",
        disabled=st.session_state.claude_concurrent_streaming_active or not question.strip(),
        type="primary"
    )

with col2:
    if st.session_state.claude_concurrent_streaming_active:
        if st.button("🛑 Stop Streaming"):
            st.session_state.stop_streaming = True
            st.session_state.claude_concurrent_streaming_active = False
            st.session_state.claude_generating_response = False
            st.session_state.claude_generating_api_response = False
            st.rerun()

with col3:
    if st.button("🔄 Clear"):
        # Clear all Claude-related session state
        st.session_state.claude_response = None
        st.session_state.claude_api_response = None
        st.session_state.claude_webui_streaming_text = ""
        st.session_state.claude_api_streaming_text = ""
        st.session_state.claude_webui_stream_complete = False
        st.session_state.claude_api_stream_complete = False
        st.session_state.claude_concurrent_streaming_active = False
        st.session_state.claude_generating_response = False
        st.session_state.claude_generating_api_response = False
        st.rerun()

# Handle send button
if send_button and question.strip():
    # Set the transcription to the question text (this is what the handler expects)
    st.session_state.transcription = question.strip()
    
    # Start Claude concurrent streaming
    claude_start_concurrent_streaming(question.strip())
    st.rerun()

# Response display using the existing handler
if question.strip():
    # Set transcription for the render function
    st.session_state.transcription = question.strip()
    
    st.subheader("🤖 Claude Response")
    
    # Use the existing render function
    render_claude_responses()
    
    # Handle concurrent streaming
    claude_handle_concurrent_streaming()

# Handle stopped streaming
claude_handle_stopped_streaming()

# Debug information (collapsible)
with st.expander("🔧 Debug Information"):
    st.write("**Claude Session State:**")
    debug_info = {
        "claude_concurrent_streaming_active": st.session_state.claude_concurrent_streaming_active,
        "claude_generating_response": st.session_state.claude_generating_response,
        "claude_generating_api_response": st.session_state.claude_generating_api_response,
        "claude_webui_stream_complete": st.session_state.claude_webui_stream_complete,
        "claude_api_stream_complete": st.session_state.claude_api_stream_complete,
        "stop_streaming": st.session_state.stop_streaming,
        "webui_response_length": len(st.session_state.claude_response or ""),
        "api_response_length": len(st.session_state.claude_api_response or ""),
        "webui_streaming_text_length": len(st.session_state.claude_webui_streaming_text),
        "api_streaming_text_length": len(st.session_state.claude_api_streaming_text)
    }
    st.json(debug_info)

# Footer
st.markdown("---")
st.markdown("""
**About this app:**
- Uses the existing `claude_handler.py` functions
- Attempts both Web UI and API streaming simultaneously
- Web UI mode may show connection errors (this is expected in Streamlit)
- API mode requires proper API key configuration

**Files used:**
- `chat_handlers/claude_handler.py` - Main handler functions
- `chat_handlers/claude_streaming_chat.py` - Playwright-based Web UI communication
""")
