import streamlit as st
import threading
import time
import os
import anthropic
from streamlit.runtime.scriptrunner import add_script_run_ctx
import datetime
import json

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, skip
    pass

# Configure page layout
st.set_page_config(
    page_title="Claude Simple Chat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
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
.stAlert > div {
    padding: 0.5rem 1rem;
}
</style>
""", unsafe_allow_html=True)

def start_thread(fn, *args, **kwargs):
    """Utility – start a daemon thread that can call Streamlit commands."""
    th = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    add_script_run_ctx(th)
    th.start()
    return th

def log_qa_pair(question: str, answer: str):
    """Log question/answer pair to session log file"""
    try:
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "question": question,
            "answer": answer,
            "model": st.session_state.selected_model
        }
        
        with open(st.session_state.session_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False, indent=2) + "\n")
            
    except Exception as e:
        st.error(f"Failed to log Q&A pair: {str(e)}")

def api_streaming_worker(question):
    """Worker thread for Claude API streaming - updates session state incrementally"""
    try:
        # Check for API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            st.session_state.claude_streaming_text = "❌ Error: ANTHROPIC_API_KEY not found in environment variables. Please set your API key."
            st.session_state.stream_complete = True
            st.session_state.generating_response = False
            return
        
        client = anthropic.Anthropic(api_key=api_key)
        
        # Add to conversation history
        st.session_state.conversation_history.append({"role": "user", "content": question})
        
        # Use conversation history - convert to Claude format
        messages = []
        for msg in st.session_state.conversation_history:
            if msg["role"] in ["user", "assistant"]:
                messages.append(msg)
        
        full_response = ""
        
        # Stream the response using Claude API
        with client.messages.stream(
            model=st.session_state.selected_model,
            max_tokens=4000,
            messages=messages
        ) as stream:
            st.session_state.claude_streaming_text = "🚀 Claude is typing..."
            
            for text in stream.text_stream:
                if st.session_state.stop_streaming:
                    break
                    
                full_response += text
                # Update session state with cursor
                st.session_state.claude_streaming_text = full_response + "▌"
        
        # Final update without cursor
        st.session_state.claude_streaming_text = full_response
        st.session_state.claude_response = full_response
        
        # Add response to conversation history
        if full_response:
            st.session_state.conversation_history.append({"role": "assistant", "content": full_response})
            
            # Log the Q&A pair
            log_qa_pair(question, full_response)
        
        st.session_state.stream_complete = True
        st.session_state.generating_response = False
        
    except Exception as e:
        error_msg = str(e)
        if "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
            st.session_state.claude_streaming_text = "❌ Authentication Error: Please check your ANTHROPIC_API_KEY environment variable."
        elif "rate_limit" in error_msg.lower():
            st.session_state.claude_streaming_text = "❌ Rate Limit Error: Please wait a moment before trying again."
        else:
            st.session_state.claude_streaming_text = f"❌ API Error: {error_msg}"
        st.session_state.stream_complete = True
        st.session_state.generating_response = False

def start_streaming(question):
    """Start Claude API streaming"""
    st.session_state.streaming_active = True
    st.session_state.claude_streaming_text = ""
    st.session_state.stream_complete = False
    st.session_state.generating_response = True
    st.session_state.stop_streaming = False
    
    # Start API streaming thread  
    start_thread(api_streaming_worker, question)

# Initialize session state variables
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "claude_response" not in st.session_state:
    st.session_state.claude_response = None
if "claude_streaming_text" not in st.session_state:
    st.session_state.claude_streaming_text = ""
if "stream_complete" not in st.session_state:
    st.session_state.stream_complete = False
if "streaming_active" not in st.session_state:
    st.session_state.streaming_active = False
if "generating_response" not in st.session_state:
    st.session_state.generating_response = False
if "stop_streaming" not in st.session_state:
    st.session_state.stop_streaming = False
if "selected_model" not in st.session_state:
    st.session_state.selected_model = "claude-3-5-sonnet-20241022"
if "session_log_file" not in st.session_state:
    LOGS_DIR = "logs"
    os.makedirs(LOGS_DIR, exist_ok=True)
    session_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.session_log_file = os.path.join(LOGS_DIR, f"claude_session_{session_timestamp}.json")

# Main UI
st.markdown('<div class="main-header">🤖 Claude Simple Chat</div>', unsafe_allow_html=True)

# API Key status check
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    st.error("⚠️ **ANTHROPIC_API_KEY not found!** Please set your API key in environment variables.")
    st.info("To set your API key:\n- Create a `.env` file with: `ANTHROPIC_API_KEY=your_key_here`\n- Or set it as an environment variable")
else:
    st.success("✅ API key found")

# Model selection
model_options = [
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022", 
    "claude-3-opus-20240229"
]

selected_model = st.selectbox(
    "Select Claude Model:",
    model_options,
    index=0,
    key="model_selector"
)
st.session_state.selected_model = selected_model

# Instructions
st.markdown("""
### How to use:
1. **Set your API key** (see status above)
2. **Enter your question** below
3. **Click Send** to get Claude's response

This version uses only the Claude API (no browser automation) for maximum compatibility.
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
        disabled=st.session_state.streaming_active or not question.strip(),
        type="primary"
    )

with col2:
    if st.session_state.streaming_active:
        if st.button("🛑 Stop Streaming"):
            st.session_state.stop_streaming = True
            st.session_state.streaming_active = False
            st.session_state.generating_response = False
            st.rerun()

with col3:
    if st.button("🔄 Clear Chat"):
        # Clear all session state
        st.session_state.conversation_history = []
        st.session_state.claude_response = None
        st.session_state.claude_streaming_text = ""
        st.session_state.stream_complete = False
        st.session_state.streaming_active = False
        st.session_state.generating_response = False
        st.rerun()

# Handle send button
if send_button and question.strip():
    start_streaming(question.strip())
    st.rerun()

# Response display
if question.strip():
    st.subheader("🤖 Claude Response")
    
    # Show generating status
    if st.session_state.generating_response:
        st.info("🔄 Claude is generating response...")
    
    # Show response
    if st.session_state.claude_streaming_text:
        st.markdown(st.session_state.claude_streaming_text)
    elif st.session_state.claude_response and not st.session_state.streaming_active:
        st.markdown(st.session_state.claude_response)
    elif not st.session_state.generating_response and not st.session_state.claude_response:
        st.info("Click **Send to Claude** to get a response")

# Handle streaming completion
if st.session_state.streaming_active:
    if st.session_state.stream_complete:
        st.session_state.streaming_active = False
        st.success("✅ Response completed!")
        st.rerun()
    else:
        # Auto-refresh for streaming
        time.sleep(0.2)
        st.rerun()

# Conversation history
if st.session_state.conversation_history:
    with st.expander("📜 Conversation History"):
        for i, msg in enumerate(st.session_state.conversation_history):
            if msg["role"] == "user":
                st.markdown(f"**You:** {msg['content']}")
            else:
                st.markdown(f"**Claude:** {msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}")

# Debug information (collapsible)
with st.expander("🔧 Debug Information"):
    st.write("**Session State:**")
    debug_info = {
        "streaming_active": st.session_state.streaming_active,
        "generating_response": st.session_state.generating_response,
        "stream_complete": st.session_state.stream_complete,
        "stop_streaming": st.session_state.stop_streaming,
        "selected_model": st.session_state.selected_model,
        "conversation_length": len(st.session_state.conversation_history),
        "response_length": len(st.session_state.claude_response or ""),
        "streaming_text_length": len(st.session_state.claude_streaming_text),
        "api_key_present": bool(api_key),
        "log_file": st.session_state.session_log_file
    }
    st.json(debug_info)

# Footer
st.markdown("---")
st.markdown("""
**About this app:**
- Uses Claude API only (no browser automation)
- Supports streaming responses
- Maintains conversation history
- Logs conversations to JSON files
- Compatible with Streamlit Cloud and local environments

**Requirements:**
- `ANTHROPIC_API_KEY` environment variable
- `anthropic` Python package
""")
