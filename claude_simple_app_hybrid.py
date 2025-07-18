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
    page_title="Claude Hybrid Chat",
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

def log_qa_pair(question: str, webui_answer: str = None, api_answer: str = None):
    """Log question/answer pair to session log file"""
    try:
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "question": question,
            "model": st.session_state.selected_model
        }
        
        if webui_answer:
            log_entry["webui_answer"] = webui_answer
        if api_answer:
            log_entry["api_answer"] = api_answer
        
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
            st.session_state.claude_webui_streaming_text = f"❌ WebUI Import Error: {str(e)}"
            st.session_state.claude_webui_stream_complete = True
            st.session_state.claude_generating_webui_response = False
            return
        
        # Initialize the bot
        bot = ChromeDebugChatBot(debug_port=9222)
        
        # Try to connect and stream
        import asyncio
        
        async def stream_webui_response():
            try:
                st.session_state.claude_webui_streaming_text = "🔄 Connecting to Claude browser tab..."
                
                if await bot.connect_to_existing_tab():
                    st.session_state.claude_webui_streaming_text = "🚀 Connected to Claude, starting response..."
                    
                    full_response = ""
                    async for chunk in bot.send_message_with_streaming(question):
                        if st.session_state.stop_streaming:
                            break
                        
                        if not chunk.startswith("Error:"):
                            full_response += chunk
                            st.session_state.claude_webui_streaming_text = full_response + "▌"
                        else:
                            st.session_state.claude_webui_streaming_text = f"❌ WebUI Error: {chunk}"
                            break
                    
                    # Final update without cursor
                    if full_response:
                        st.session_state.claude_webui_streaming_text = full_response
                        st.session_state.claude_webui_response = full_response
                        st.session_state.conversation_history.append({"role": "user", "content": question})
                        st.session_state.conversation_history.append({"role": "assistant", "content": full_response})
                else:
                    st.session_state.claude_webui_streaming_text = "❌ Could not connect to Claude browser tab. Make sure Chrome is running with debug enabled and Claude.ai is open."
                    
            except Exception as e:
                error_msg = str(e)
                if "NotImplementedError" in error_msg or "subprocess" in error_msg:
                    st.session_state.claude_webui_streaming_text = "❌ WebUI mode not supported in this environment. Subprocess creation failed."
                else:
                    st.session_state.claude_webui_streaming_text = f"❌ WebUI Connection Error: {error_msg}"
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
                st.session_state.claude_webui_streaming_text = "❌ WebUI mode not supported in this environment. Please use API-only mode."
            else:
                st.session_state.claude_webui_streaming_text = f"❌ WebUI Runtime Error: {error_msg}"
        finally:
            try:
                loop.close()
            except:
                pass
        
        st.session_state.claude_webui_stream_complete = True
        st.session_state.claude_generating_webui_response = False
        
    except Exception as e:
        st.session_state.claude_webui_streaming_text = f"❌ WebUI Worker Error: {str(e)}"
        st.session_state.claude_webui_stream_complete = True
        st.session_state.claude_generating_webui_response = False

def api_streaming_worker(question):
    """Worker thread for Claude API streaming"""
    try:
        # Check for API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            st.session_state.claude_api_streaming_text = "❌ Error: ANTHROPIC_API_KEY not found in environment variables. Please set your API key."
            st.session_state.claude_api_stream_complete = True
            st.session_state.claude_generating_api_response = False
            return
        
        client = anthropic.Anthropic(api_key=api_key)
        
        # Use separate API conversation history
        if "api_conversation_history" not in st.session_state:
            st.session_state.api_conversation_history = []
        
        st.session_state.api_conversation_history.append({"role": "user", "content": question})
        
        messages = []
        for msg in st.session_state.api_conversation_history:
            if msg["role"] in ["user", "assistant"]:
                messages.append(msg)
        
        full_response = ""
        
        # Stream the response using Claude API
        with client.messages.stream(
            model=st.session_state.selected_model,
            max_tokens=4000,
            messages=messages
        ) as stream:
            st.session_state.claude_api_streaming_text = "🚀 Claude API is typing..."
            
            for text in stream.text_stream:
                if st.session_state.stop_streaming:
                    break
                    
                full_response += text
                st.session_state.claude_api_streaming_text = full_response + "▌"
        
        # Final update without cursor
        st.session_state.claude_api_streaming_text = full_response
        st.session_state.claude_api_response = full_response
        
        # Add response to API conversation history
        if full_response:
            st.session_state.api_conversation_history.append({"role": "assistant", "content": full_response})
        
        st.session_state.claude_api_stream_complete = True
        st.session_state.claude_generating_api_response = False
        
    except Exception as e:
        error_msg = str(e)
        if "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
            st.session_state.claude_api_streaming_text = "❌ Authentication Error: Please check your ANTHROPIC_API_KEY environment variable."
        elif "rate_limit" in error_msg.lower():
            st.session_state.claude_api_streaming_text = "❌ Rate Limit Error: Please wait a moment before trying again."
        else:
            st.session_state.claude_api_streaming_text = f"❌ API Error: {error_msg}"
        st.session_state.claude_api_stream_complete = True
        st.session_state.claude_generating_api_response = False

def start_concurrent_streaming(question):
    """Start both WebUI and API streaming concurrently"""
    st.session_state.concurrent_streaming_active = True
    st.session_state.claude_webui_streaming_text = ""
    st.session_state.claude_api_streaming_text = ""
    st.session_state.claude_webui_stream_complete = False
    st.session_state.claude_api_stream_complete = False
    st.session_state.claude_generating_webui_response = True
    st.session_state.claude_generating_api_response = True
    st.session_state.stop_streaming = False
    
    # Start both streaming threads
    if st.session_state.enable_webui:
        start_thread(webui_streaming_worker, question)
    else:
        st.session_state.claude_webui_streaming_text = "WebUI disabled by user"
        st.session_state.claude_webui_stream_complete = True
        st.session_state.claude_generating_webui_response = False
    
    if st.session_state.enable_api:
        start_thread(api_streaming_worker, question)
    else:
        st.session_state.claude_api_streaming_text = "API disabled by user"
        st.session_state.claude_api_stream_complete = True
        st.session_state.claude_generating_api_response = False

# Initialize session state variables
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "api_conversation_history" not in st.session_state:
    st.session_state.api_conversation_history = []
if "claude_webui_response" not in st.session_state:
    st.session_state.claude_webui_response = None
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
if "concurrent_streaming_active" not in st.session_state:
    st.session_state.concurrent_streaming_active = False
if "claude_generating_webui_response" not in st.session_state:
    st.session_state.claude_generating_webui_response = False
if "claude_generating_api_response" not in st.session_state:
    st.session_state.claude_generating_api_response = False
if "stop_streaming" not in st.session_state:
    st.session_state.stop_streaming = False
if "selected_model" not in st.session_state:
    st.session_state.selected_model = "claude-3-5-sonnet-20241022"
if "enable_webui" not in st.session_state:
    st.session_state.enable_webui = True
if "enable_api" not in st.session_state:
    st.session_state.enable_api = True
if "session_log_file" not in st.session_state:
    LOGS_DIR = "logs"
    os.makedirs(LOGS_DIR, exist_ok=True)
    session_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.session_log_file = os.path.join(LOGS_DIR, f"claude_session_{session_timestamp}.json")

# Main UI
st.markdown('<div class="main-header">🤖 Claude Hybrid Chat (WebUI + API)</div>', unsafe_allow_html=True)

# Configuration section
st.subheader("⚙️ Configuration")
col1, col2 = st.columns(2)

with col1:
    st.session_state.enable_webui = st.checkbox(
        "🌐 Enable WebUI Mode", 
        value=st.session_state.enable_webui,
        help="Uses Chrome debug protocol to interact with Claude.ai in browser"
    )

with col2:
    st.session_state.enable_api = st.checkbox(
        "⚡ Enable API Mode", 
        value=st.session_state.enable_api,
        help="Uses Claude API directly (requires API key)"
    )

# API Key status check
api_key = os.getenv("ANTHROPIC_API_KEY")
if st.session_state.enable_api:
    if not api_key:
        st.error("⚠️ **ANTHROPIC_API_KEY not found!** Please set your API key in environment variables.")
        st.info("To set your API key:\n- Create a `.env` file with: `ANTHROPIC_API_KEY=your_key_here`\n- Or set it as an environment variable")
    else:
        st.success("✅ API key found")

# WebUI status check
if st.session_state.enable_webui:
    st.info("🌐 **WebUI Mode**: Make sure Chrome is running with debug mode:\n`chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug`")

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
        disabled=st.session_state.concurrent_streaming_active or not question.strip() or (not st.session_state.enable_webui and not st.session_state.enable_api),
        type="primary"
    )

with col2:
    if st.session_state.concurrent_streaming_active:
        if st.button("🛑 Stop Streaming"):
            st.session_state.stop_streaming = True
            st.session_state.concurrent_streaming_active = False
            st.session_state.claude_generating_webui_response = False
            st.session_state.claude_generating_api_response = False
            st.rerun()

with col3:
    if st.button("🔄 Clear Chat"):
        # Clear all session state
        st.session_state.conversation_history = []
        st.session_state.api_conversation_history = []
        st.session_state.claude_webui_response = None
        st.session_state.claude_api_response = None
        st.session_state.claude_webui_streaming_text = ""
        st.session_state.claude_api_streaming_text = ""
        st.session_state.claude_webui_stream_complete = False
        st.session_state.claude_api_stream_complete = False
        st.session_state.concurrent_streaming_active = False
        st.session_state.claude_generating_webui_response = False
        st.session_state.claude_generating_api_response = False
        st.rerun()

# Handle send button
if send_button and question.strip():
    start_concurrent_streaming(question.strip())
    st.rerun()

# Response display
if question.strip():
    st.subheader("🤖 Claude Responses")
    
    # Show generating status
    if st.session_state.claude_generating_webui_response or st.session_state.claude_generating_api_response:
        active_streams = []
        if st.session_state.claude_generating_webui_response:
            active_streams.append("WebUI")
        if st.session_state.claude_generating_api_response:
            active_streams.append("API")
        st.info(f"🔄 Generating responses: {', '.join(active_streams)}")

    # Two side-by-side panes for concurrent responses
    col_web, col_api = st.columns(2)

    # WebUI pane
    with col_web:
        st.markdown('<div class="box-header">🌐 Web UI</div>', unsafe_allow_html=True)
        
        if st.session_state.enable_webui:
            if st.session_state.claude_webui_streaming_text:
                st.markdown(st.session_state.claude_webui_streaming_text)
            elif st.session_state.claude_webui_response and not st.session_state.concurrent_streaming_active:
                st.markdown(st.session_state.claude_webui_response)
            elif st.session_state.claude_generating_webui_response:
                st.info("WebUI response will appear here...")
            else:
                st.info("Click **Send to Claude** to generate WebUI response")
        else:
            st.info("WebUI mode is disabled")

    # API pane
    with col_api:
        st.markdown('<div class="box-header">⚡ API</div>', unsafe_allow_html=True)
        
        if st.session_state.enable_api:
            if st.session_state.claude_api_streaming_text:
                st.markdown(st.session_state.claude_api_streaming_text)
            elif st.session_state.claude_api_response and not st.session_state.concurrent_streaming_active:
                st.markdown(st.session_state.claude_api_response)
            elif st.session_state.claude_generating_api_response:
                st.info("API response will appear here...")
            else:
                st.info("Click **Send to Claude** to generate API response")
        else:
            st.info("API mode is disabled")

# Handle streaming completion
if st.session_state.concurrent_streaming_active:
    # Check if both streams are complete (or disabled)
    webui_done = st.session_state.claude_webui_stream_complete or not st.session_state.enable_webui
    api_done = st.session_state.claude_api_stream_complete or not st.session_state.enable_api
    
    if webui_done and api_done:
        st.session_state.concurrent_streaming_active = False
        
        # Log both responses when both streams are complete
        log_qa_pair(
            question.strip(),
            webui_answer=st.session_state.claude_webui_response if st.session_state.enable_webui else None,
            api_answer=st.session_state.claude_api_response if st.session_state.enable_api else None
        )
        
        st.success("✅ All enabled responses completed!")
        st.rerun()
    else:
        # Auto-refresh for streaming
        time.sleep(0.2)
        st.rerun()

# Conversation history
if st.session_state.conversation_history or st.session_state.api_conversation_history:
    with st.expander("📜 Conversation History"):
        if st.session_state.conversation_history:
            st.write("**WebUI Conversation:**")
            for i, msg in enumerate(st.session_state.conversation_history):
                if msg["role"] == "user":
                    st.markdown(f"**You:** {msg['content']}")
                else:
                    st.markdown(f"**Claude:** {msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}")
        
        if st.session_state.api_conversation_history:
            st.write("**API Conversation:**")
            for i, msg in enumerate(st.session_state.api_conversation_history):
                if msg["role"] == "user":
                    st.markdown(f"**You:** {msg['content']}")
                else:
                    st.markdown(f"**Claude:** {msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}")

# Debug information (collapsible)
with st.expander("🔧 Debug Information"):
    st.write("**Session State:**")
    debug_info = {
        "concurrent_streaming_active": st.session_state.concurrent_streaming_active,
        "claude_generating_webui_response": st.session_state.claude_generating_webui_response,
        "claude_generating_api_response": st.session_state.claude_generating_api_response,
        "claude_webui_stream_complete": st.session_state.claude_webui_stream_complete,
        "claude_api_stream_complete": st.session_state.claude_api_stream_complete,
        "stop_streaming": st.session_state.stop_streaming,
        "selected_model": st.session_state.selected_model,
        "enable_webui": st.session_state.enable_webui,
        "enable_api": st.session_state.enable_api,
        "webui_conversation_length": len(st.session_state.conversation_history),
        "api_conversation_length": len(st.session_state.api_conversation_history),
        "webui_response_length": len(st.session_state.claude_webui_response or ""),
        "api_response_length": len(st.session_state.claude_api_response or ""),
        "api_key_present": bool(api_key),
        "log_file": st.session_state.session_log_file
    }
    st.json(debug_info)

# Footer
st.markdown("---")
st.markdown("""
**About this app:**
- **Hybrid Mode**: Supports both WebUI (browser automation) and API modes
- **Concurrent Streaming**: Can run both modes simultaneously for comparison
- **Flexible Configuration**: Enable/disable each mode independently
- **Better Error Handling**: WebUI errors won't crash the app
- **Separate Conversation Histories**: WebUI and API maintain separate contexts

**Requirements:**
- **For API Mode**: `ANTHROPIC_API_KEY` environment variable
- **For WebUI Mode**: Chrome with debug mode enabled
- **Dependencies**: `streamlit`, `anthropic`, `playwright` (for WebUI)
""")
