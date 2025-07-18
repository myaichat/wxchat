import streamlit as st
import threading
import time
import os
import json
import requests
import websocket
import datetime
from streamlit.runtime.scriptrunner import add_script_run_ctx

# Configure page layout
st.set_page_config(
    page_title="Claude WebUI Direct CDP",
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
            "mode": "direct_cdp"
        }
        
        with open(st.session_state.session_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False, indent=2) + "\n")
            
    except Exception as e:
        st.error(f"Failed to log Q&A pair: {str(e)}")

class DirectCDPClaude:
    def __init__(self, debug_port=9222):
        self.debug_port = debug_port
        self.ws = None
        self.tab_id = None
        self.session_id = None
        
    def get_tabs(self):
        """Get list of Chrome tabs via HTTP"""
        try:
            response = requests.get(f"http://localhost:{self.debug_port}/json", timeout=5)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            st.session_state.claude_streaming_text = f"❌ Failed to connect to Chrome debug port {self.debug_port}: {str(e)}"
            return []
    
    def find_claude_tab(self, tabs):
        """Find Claude.ai tab"""
        for tab in tabs:
            url = tab.get('url', '').lower()
            if 'claude.ai' in url:
                return tab
        return None
    
    def connect_to_tab(self, tab):
        """Connect to Chrome tab via WebSocket"""
        try:
            ws_url = tab['webSocketDebuggerUrl']
            self.ws = websocket.create_connection(ws_url, timeout=10)
            self.tab_id = tab['id']
            return True
        except Exception as e:
            st.session_state.claude_streaming_text = f"❌ Failed to connect to WebSocket: {str(e)}"
            return False
    
    def send_cdp_command(self, method, params=None):
        """Send CDP command"""
        if not self.ws:
            return None
            
        command = {
            "id": int(time.time() * 1000),
            "method": method,
            "params": params or {}
        }
        
        try:
            self.ws.send(json.dumps(command))
            response = self.ws.recv()
            return json.loads(response)
        except Exception as e:
            st.session_state.claude_streaming_text = f"❌ CDP command failed: {str(e)}"
            return None
    
    def get_page_content(self):
        """Get page content"""
        result = self.send_cdp_command("Runtime.evaluate", {
            "expression": "document.body.innerText"
        })
        if result and 'result' in result and 'value' in result['result']:
            return result['result']['value']
        return ""
    
    def find_input_element(self):
        """Find the message input element"""
        # Try different selectors for Claude's input
        selectors = [
            '[contenteditable="true"]',
            'textarea[placeholder*="message"]',
            'textarea[placeholder*="Message"]',
            'textarea',
            'div[contenteditable="true"]'
        ]
        
        for selector in selectors:
            result = self.send_cdp_command("Runtime.evaluate", {
                "expression": f"document.querySelector('{selector}')"
            })
            if result and 'result' in result and result['result'].get('type') != 'null':
                return selector
        return None
    
    def type_message(self, selector, message):
        """Type message into input element"""
        # Focus the element
        self.send_cdp_command("Runtime.evaluate", {
            "expression": f"document.querySelector('{selector}').focus()"
        })
        
        # Clear existing content
        self.send_cdp_command("Runtime.evaluate", {
            "expression": f"document.querySelector('{selector}').innerText = ''"
        })
        
        # Type the message
        for char in message:
            self.send_cdp_command("Input.dispatchKeyEvent", {
                "type": "char",
                "text": char
            })
            time.sleep(0.01)  # Small delay between characters
    
    def find_send_button(self):
        """Find and click send button"""
        selectors = [
            'button[aria-label*="send"]',
            'button[title*="send"]',
            'button[data-testid*="send"]',
            'button:has-text("Send")',
            'button[type="submit"]'
        ]
        
        for selector in selectors:
            result = self.send_cdp_command("Runtime.evaluate", {
                "expression": f"document.querySelector('{selector}')"
            })
            if result and 'result' in result and result['result'].get('type') != 'null':
                # Click the button
                self.send_cdp_command("Runtime.evaluate", {
                    "expression": f"document.querySelector('{selector}').click()"
                })
                return True
        
        # Fallback: try pressing Enter
        self.send_cdp_command("Input.dispatchKeyEvent", {
            "type": "keyDown",
            "key": "Enter"
        })
        self.send_cdp_command("Input.dispatchKeyEvent", {
            "type": "keyUp", 
            "key": "Enter"
        })
        return True
    
    def monitor_response(self, initial_content, question):
        """Monitor for Claude's response"""
        last_content = initial_content
        response_text = ""
        no_change_count = 0
        max_iterations = 60
        
        for i in range(max_iterations):
            if st.session_state.stop_streaming:
                break
                
            time.sleep(0.5)
            current_content = self.get_page_content()
            
            if current_content and len(current_content) > len(last_content):
                # New content detected
                new_text = current_content[len(last_content):]
                
                # Filter out UI elements and extract actual response
                lines = new_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if (line and 
                        not line.startswith('Send') and
                        not line.startswith('Type') and
                        not line.startswith('Edit') and
                        not line.startswith('Copy') and
                        question.lower() not in line.lower() and
                        len(line) > 3):
                        response_text += line + "\n"
                        st.session_state.claude_streaming_text = response_text + "▌"
                
                last_content = current_content
                no_change_count = 0
            else:
                no_change_count += 1
                if no_change_count > 6:  # 3 seconds of no changes
                    break
        
        return response_text.strip()
    
    def close(self):
        """Close WebSocket connection"""
        if self.ws:
            try:
                self.ws.close()
            except:
                pass

def direct_cdp_worker(question):
    """Worker thread using direct CDP communication"""
    bot = DirectCDPClaude(debug_port=9222)
    
    try:
        st.session_state.claude_streaming_text = "🔄 Getting Chrome tabs..."
        
        # Get tabs
        tabs = bot.get_tabs()
        if not tabs:
            st.session_state.claude_streaming_text = """❌ No Chrome tabs found. 

**Please ensure:**
1. Chrome is running with debug mode: `chrome --remote-debugging-port=9222`
2. Chrome is actually running and accessible
3. No firewall is blocking port 9222"""
            return
        
        st.session_state.claude_streaming_text = f"🔄 Found {len(tabs)} tabs, looking for Claude.ai..."
        
        # Find Claude tab
        claude_tab = bot.find_claude_tab(tabs)
        if not claude_tab:
            st.session_state.claude_streaming_text = """❌ No Claude.ai tab found.

**Please ensure:**
1. Claude.ai is open in Chrome
2. You're logged into Claude.ai
3. The tab is active and loaded"""
            return
        
        st.session_state.claude_streaming_text = f"🔄 Found Claude tab: {claude_tab.get('title', 'Unknown')}"
        
        # Connect to tab
        if not bot.connect_to_tab(claude_tab):
            return
        
        st.session_state.claude_streaming_text = "🔄 Connected via WebSocket, finding input element..."
        
        # Get initial page content
        initial_content = bot.get_page_content()
        
        # Find input element
        input_selector = bot.find_input_element()
        if not input_selector:
            st.session_state.claude_streaming_text = """❌ Could not find message input element.

**This might happen if:**
1. Claude.ai page hasn't fully loaded
2. You're not logged in
3. The page structure has changed
4. You're on the wrong page (not a chat page)"""
            return
        
        st.session_state.claude_streaming_text = f"🔄 Found input element, typing message..."
        
        # Type message
        bot.type_message(input_selector, question)
        
        st.session_state.claude_streaming_text = "🔄 Message typed, sending..."
        
        # Send message
        bot.find_send_button()
        
        st.session_state.claude_streaming_text = "🚀 Message sent, waiting for response..."
        
        # Monitor response
        response = bot.monitor_response(initial_content, question)
        
        if response:
            st.session_state.claude_streaming_text = response
            st.session_state.claude_response = response
            
            # Add to conversation history
            st.session_state.conversation_history.append({"role": "user", "content": question})
            st.session_state.conversation_history.append({"role": "assistant", "content": response})
            
            # Log the Q&A pair
            log_qa_pair(question, response)
        else:
            st.session_state.claude_streaming_text = "❌ No response received. The page might not have updated or Claude might be processing."
        
    except Exception as e:
        st.session_state.claude_streaming_text = f"❌ Direct CDP Error: {str(e)}"
    finally:
        bot.close()
        st.session_state.stream_complete = True
        st.session_state.generating_response = False

def start_streaming(question):
    """Start direct CDP streaming"""
    st.session_state.streaming_active = True
    st.session_state.claude_streaming_text = ""
    st.session_state.stream_complete = False
    st.session_state.generating_response = True
    st.session_state.stop_streaming = False
    
    # Start direct CDP thread
    start_thread(direct_cdp_worker, question)

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
    st.session_state.session_log_file = os.path.join(LOGS_DIR, f"claude_cdp_session_{session_timestamp}.json")

# Main UI
st.markdown('<div class="main-header">🌐 Claude WebUI Direct CDP</div>', unsafe_allow_html=True)

# Status and instructions
st.subheader("🌐 Direct CDP Mode")
st.info("""
**This version bypasses Playwright entirely and uses direct Chrome DevTools Protocol (CDP) communication.**

**Prerequisites:**
1. **Start Chrome with debug mode:**
   ```
   chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
   ```
   Or use: `start_chrome_for_claude.bat`

2. **Open Claude.ai** in Chrome and log in

3. **Enter your question** below and click Send

**How it works:**
- Uses HTTP requests to get Chrome tabs
- Connects directly via WebSocket to Chrome
- Sends CDP commands to interact with the page
- No subprocess creation - should work in all environments
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
        "🚀 Send to Claude (Direct CDP)",
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
        st.info("🔄 Claude is generating response via Direct CDP...")
    
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
        st.success("✅ Direct CDP response completed!")
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
**About this Direct CDP version:**
- **No Playwright**: Bypasses all Playwright subprocess issues
- **Direct WebSocket**: Connects directly to Chrome via WebSocket
- **CDP Commands**: Uses Chrome DevTools Protocol for page interaction
- **Universal Compatibility**: Should work in all Windows/Streamlit environments
- **Real-time Streaming**: Monitors page changes for response updates

**Requirements:**
- **Chrome with debug mode**: `chrome --remote-debugging-port=9222`
- **Claude.ai account**: Must be logged in
- **Dependencies**: `streamlit`, `requests`, `websocket-client` (no Playwright needed)

**Technical approach:**
1. HTTP request to get Chrome tabs
2. WebSocket connection to Claude tab
3. CDP commands to find input and type message
4. CDP commands to click send button
5. Page content monitoring for response
""")
