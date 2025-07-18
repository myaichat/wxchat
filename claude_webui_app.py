import streamlit as st
import asyncio
import threading
import time
from streamlit.runtime.scriptrunner import add_script_run_ctx

# Configure page layout
st.set_page_config(
    page_title="Claude Web UI Chat",
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
.status-box {
    padding: 10px;
    border-radius: 5px;
    margin: 10px 0;
}
.success-box {
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
    color: #155724;
}
.error-box {
    background-color: #f8d7da;
    border: 1px solid #f5c6cb;
    color: #721c24;
}
.info-box {
    background-color: #d1ecf1;
    border: 1px solid #bee5eb;
    color: #0c5460;
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "claude_response" not in st.session_state:
    st.session_state.claude_response = ""
if "streaming_text" not in st.session_state:
    st.session_state.streaming_text = ""
if "is_streaming" not in st.session_state:
    st.session_state.is_streaming = False
if "stream_complete" not in st.session_state:
    st.session_state.stream_complete = False
if "stop_streaming" not in st.session_state:
    st.session_state.stop_streaming = False
if "connection_status" not in st.session_state:
    st.session_state.connection_status = "Not connected"

def start_thread(fn, *args, **kwargs):
    """Start a daemon thread that can call Streamlit commands."""
    th = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    add_script_run_ctx(th)
    th.start()
    return th

def claude_streaming_worker(question):
    """Worker thread for Claude Web UI streaming"""
    try:
        # Import the ChromeDebugChatBot
        from chat_handlers.claude_streaming_chat import ChromeDebugChatBot
        
        st.session_state.connection_status = "Connecting to Chrome..."
        st.session_state.streaming_text = "🔄 Initializing connection to Claude..."
        
        # Create event loop for async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def stream_response():
            bot = None
            try:
                # Create bot instance
                bot = ChromeDebugChatBot(debug_port=9222)
                
                st.session_state.connection_status = "Connecting to Claude tab..."
                st.session_state.streaming_text = "🔄 Connecting to Claude browser tab..."
                
                # Connect to existing Chrome tab
                if await bot.connect_to_existing_tab():
                    st.session_state.connection_status = "Connected - Sending message"
                    st.session_state.streaming_text = "🚀 Connected! Sending message to Claude..."
                    
                    full_response = ""
                    
                    # Stream the response
                    async for chunk in bot.send_message_with_streaming(question):
                        if st.session_state.stop_streaming:
                            st.session_state.streaming_text = "🛑 Streaming stopped by user"
                            break
                        
                        if not chunk.startswith("Error:"):
                            full_response += chunk
                            # Update session state with streaming content and cursor
                            st.session_state.streaming_text = full_response + "▌"
                        else:
                            st.session_state.streaming_text = f"❌ Streaming error: {chunk}"
                            st.session_state.connection_status = "Error during streaming"
                            break
                    
                    # Final update without cursor
                    if not st.session_state.stop_streaming:
                        st.session_state.streaming_text = full_response
                        st.session_state.claude_response = full_response
                        st.session_state.connection_status = "Response completed"
                    
                else:
                    st.session_state.streaming_text = "❌ Could not connect to Claude browser tab"
                    st.session_state.connection_status = "Connection failed"
                    
            except Exception as e:
                error_msg = str(e)
                if "NotImplementedError" in error_msg or "subprocess" in error_msg:
                    st.session_state.streaming_text = "❌ Subprocess creation failed. Please ensure Chrome is running with debug mode: chrome --remote-debugging-port=9222"
                    st.session_state.connection_status = "Subprocess error"
                else:
                    st.session_state.streaming_text = f"❌ Connection error: {error_msg}"
                    st.session_state.connection_status = f"Error: {error_msg}"
                    
            finally:
                if bot:
                    try:
                        await bot.close()
                    except:
                        pass
        
        # Run the async streaming
        loop.run_until_complete(stream_response())
        
    except Exception as e:
        error_msg = str(e)
        if "NotImplementedError" in error_msg or "subprocess" in error_msg:
            st.session_state.streaming_text = "❌ Playwright subprocess not supported in this environment. Please run Chrome manually with debug mode."
            st.session_state.connection_status = "Environment limitation"
        else:
            st.session_state.streaming_text = f"❌ Import or execution error: {error_msg}"
            st.session_state.connection_status = f"Error: {error_msg}"
    finally:
        st.session_state.is_streaming = False
        st.session_state.stream_complete = True
        try:
            loop.close()
        except:
            pass

# Main UI
st.markdown('<div class="main-header">🤖 Claude Web UI Chat</div>', unsafe_allow_html=True)

# Instructions
st.markdown("""
### Prerequisites
1. **Start Chrome with debug mode:**
   ```bash
   chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
   ```
2. **Open Claude.ai** in the Chrome browser
3. **Enter your question** below and click Send

### Connection Status
""")

# Status indicator
status_color = "info-box"
if "Connected" in st.session_state.connection_status:
    status_color = "success-box"
elif "Error" in st.session_state.connection_status or "failed" in st.session_state.connection_status:
    status_color = "error-box"

st.markdown(f'<div class="status-box {status_color}">Status: {st.session_state.connection_status}</div>', unsafe_allow_html=True)

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
        disabled=st.session_state.is_streaming or not question.strip(),
        type="primary"
    )

with col2:
    if st.session_state.is_streaming:
        if st.button("🛑 Stop"):
            st.session_state.stop_streaming = True

with col3:
    if st.button("🔄 Clear"):
        st.session_state.claude_response = ""
        st.session_state.streaming_text = ""
        st.session_state.connection_status = "Not connected"
        st.rerun()

# Handle send button
if send_button and question.strip():
    st.session_state.is_streaming = True
    st.session_state.stream_complete = False
    st.session_state.stop_streaming = False
    st.session_state.claude_response = ""
    st.session_state.streaming_text = ""
    
    # Start streaming in background thread
    start_thread(claude_streaming_worker, question.strip())
    st.rerun()

# Response display
st.subheader("🤖 Claude's Response")

if st.session_state.is_streaming:
    st.info("🔄 Streaming response from Claude...")
    
    # Show live streaming text
    if st.session_state.streaming_text:
        response_container = st.container()
        with response_container:
            st.markdown(st.session_state.streaming_text)
    
    # Auto-refresh while streaming
    if st.session_state.is_streaming and not st.session_state.stream_complete:
        time.sleep(0.5)
        st.rerun()

elif st.session_state.claude_response:
    # Show final response
    st.markdown("### Final Response:")
    st.markdown(st.session_state.claude_response)
    
elif st.session_state.streaming_text and not st.session_state.is_streaming:
    # Show error or status message
    if st.session_state.streaming_text.startswith("❌"):
        st.error(st.session_state.streaming_text)
    else:
        st.info(st.session_state.streaming_text)
        
else:
    st.info("Enter a question above and click 'Send to Claude' to get started.")

# Debug information (collapsible)
with st.expander("🔧 Debug Information"):
    st.write("**Session State:**")
    debug_info = {
        "is_streaming": st.session_state.is_streaming,
        "stream_complete": st.session_state.stream_complete,
        "stop_streaming": st.session_state.stop_streaming,
        "connection_status": st.session_state.connection_status,
        "response_length": len(st.session_state.claude_response),
        "streaming_text_length": len(st.session_state.streaming_text)
    }
    st.json(debug_info)

# Footer
st.markdown("---")
st.markdown("""
**Troubleshooting:**
- If you see connection errors, make sure Chrome is running with debug mode
- If you see subprocess errors, this is a Windows/Streamlit limitation
- The standalone script `ask_claude_handler.py` works better for testing
""")
