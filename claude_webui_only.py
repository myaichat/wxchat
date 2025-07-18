import streamlit as st
import threading
import time
import os
from streamlit.runtime.scriptrunner import add_script_run_ctx
import datetime
import json

# Configure page layout
st.set_page_config(
    page_title="Claude WebUI Chat",
    page_icon="🌐",
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
            "webui_answer": answer,
            "mode": "webui_only"
        }
        
        with open(st.session_state.session_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False, indent=2) + "\n")
            
    except Exception as e:
        st.error(f"Failed to log Q&A pair: {str(e)}")

def webui_streaming_worker(question):
    """Worker thread for WebUI streaming - with better error handling"""
    try:
        # Try to import the WebUI handler
        try:
            from chat_handlers.claude_streaming_chat_streamlit_fix import ChromeDebugChatBot
        except ImportError as e:
            st.session_state.claude_streaming_text = f"❌ WebUI Import Error: {str(e)}\n\nMake sure the required dependencies are installed:\n- playwright\n- websockets"
            st.session_state.stream_complete = True
            st.session_state.generating_response = False
            return
        
        # Initialize the bot
        bot = ChromeDebugChatBot(debug_port=9222)
        
        # Try to connect and stream
        import asyncio
        
        async def stream_webui_response():
            try:
                st.session_state.claude_streaming_text = "🔄 Connecting to Claude browser tab..."
                
                if await bot.connect_to_existing_tab():
                    st.session_state.claude_streaming_text = "🚀 Connected to Claude, starting response..."
                    
                    full_response = ""
                    async for chunk in bot.send_message_with_streaming(question):
                        if st.session_state.stop_streaming:
                            break
                        
                        if not chunk.startswith("Error:"):
                            full_response += chunk
                            st.session_state.claude_streaming_text = full_response + "▌"
                        else:
                            st.session_state.claude_streaming_text = f"❌ WebUI Error: {chunk}"
                            break
                    
                    # Final update without cursor
                    if full_response:
                        st.session_state.claude_streaming_text = full_response
                        st.session_state.claude_response = full_response
                        
                        # Add to conversation history
                        st.session_state.conversation_history.append({"role": "user", "content": question})
                        st.session_state.conversation_history.append({"role": "assistant", "content": full_response})
                        
                        # Log the Q&A pair
                        log_qa_pair(question, full_response)
                else:
                    st.session_state.claude_streaming_text = """❌ Could not connect to Claude browser tab. 

**Please ensure:**
1. Chrome is running with debug mode enabled
2. Claude.ai is open in a browser tab
3. You're logged into Claude.ai

**To start Chrome with debug mode:**
```
chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
```

Or use the provided batch file: `start_chrome_for_claude.bat`"""
                    
            except Exception as e:
                error_msg = str(e)
                if "NotImplementedError" in error_msg or "subprocess" in error_msg:
                    st.session_state.claude_streaming_text = """❌ WebUI mode not supported in this environment. 

**Issue:** Subprocess creation failed (common in some Windows/Streamlit environments)

**Solutions:**
1. Try running Chrome debug mode manually first
2. Use a different terminal/environment
3. Check if Windows Defender or antivirus is blocking subprocess creation"""
                else:
                    st.session_state.claude_streaming_text = f"❌ WebUI Connection Error: {error_msg}"
            finally:
                if bot:
                    try:
                        await bot.close()
                    except:
                        pass
        
        # Run the async function
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(stream_webui_response())
        except Exception as e:
            error_msg = str(e)
            if "NotImplementedError" in error_msg:
                st.session_state.claude_streaming_text = """❌ WebUI mode not supported in this environment.

**Issue:** Async event loop creation failed

**This can happen when:**
- Running in certain Windows environments
- Streamlit subprocess restrictions
- Python event loop conflicts

**Try:**
- Running from a different terminal
- Using a different Python environment
- Running Chrome debug mode manually before starting the app"""
            else:
                st.session_state.claude_streaming_text = f"❌ WebUI Runtime Error: {error_msg}"
        finally:
            try:
                loop.close()
            except:
                pass
        
        st.session_state.stream_complete = True
        st.session_state.generating_response = False
        
    except Exception as e:
        st.session_state.claude_streaming_text = f"❌ WebUI Worker Error: {str(e)}"
        st.session_state.stream_complete = True
        st.session_state.generating_response = False

def start_streaming(question):
    """Start WebUI streaming"""
    st.session_state.streaming_active = True
    st.session_state.claude_streaming_text = ""
    st.session_state.stream_complete = False
    st.session_state.generating_response = True
    st.session_state.stop_streaming = False
    
    # Start WebUI streaming thread
    start_thread(webui_streaming_worker, question)

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
if "session_log_file" not in st.session_state:
    LOGS_DIR = "logs"
    os.makedirs(LOGS_DIR, exist_ok=True)
    session_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.session_log_file = os.path.join(LOGS_DIR, f"claude_webui_session_{session_timestamp}.json")

# Main UI
st.markdown('<div class="main-header">🌐 Claude WebUI Chat</div>', unsafe_allow_html=True)

# WebUI status and instructions
st.subheader("🌐 WebUI Mode Setup")
st.info("""
**Prerequisites for WebUI Mode:**

1. **Start Chrome with debug mode:**
   ```
   chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
   ```
   Or use: `start_chrome_for_claude.bat`

2. **Open Claude.ai** in Chrome and log in

3. **Enter your question** below and click Send

**Note:** WebUI mode uses browser automation to interact with Claude.ai directly.
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
        st.info("🔄 Claude is generating response via WebUI...")
    
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
        st.success("✅ WebUI response completed!")
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
        "conversation_length": len(st.session_state.conversation_history),
        "response_length": len(st.session_state.claude_response or ""),
        "streaming_text_length": len(st.session_state.claude_streaming_text),
        "log_file": st.session_state.session_log_file
    }
    st.json(debug_info)

# Footer
st.markdown("---")
st.markdown("""
**About this app:**
- **WebUI Only**: Uses browser automation to interact with Claude.ai directly
- **Streaming Responses**: Real-time response updates as Claude types
- **Conversation History**: Maintains chat context across messages
- **Session Logging**: Saves conversations to JSON files
- **Better Error Handling**: Clear error messages and troubleshooting guidance

**Requirements:**
- **Chrome with debug mode**: `chrome --remote-debugging-port=9222`
- **Claude.ai account**: Must be logged in
- **Dependencies**: `streamlit`, `playwright`, `websockets`

**Files used:**
- `chat_handlers/claude_streaming_chat_streamlit_fix.py` - WebUI communication handler
""")
