import streamlit as st
import pychrome
import time
import traceback

# Initialize session state
if 'browser' not in st.session_state:
    st.session_state.browser = None
if 'tab' not in st.session_state:
    st.session_state.tab = None
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

def connect_to_browser():
    """Connect to Chrome browser and find the specific tab"""
    try:
        # Connect to the browser
        browser = pychrome.Browser(url="http://localhost:9222")
        
        # Find the specific tab by ID
        tab_id = "8D25B8EDED124ED7635252EF0F0E4217"
        tabs = browser.list_tab()
        tab = None
        for t in tabs:
            if t.id == tab_id:
                tab = t
                break
        
        if tab is None:
            st.error("Tab with specified ID not found. Available tabs:")
            for t in tabs:
                st.write(f"- ID: {t.id}, URL: {t.url}")
            return None, None
        
        # Start the tab
        tab.start()
        
        # Enable Runtime domain
        tab.call_method("Runtime.enable")
        
        return browser, tab
    except Exception as e:
        st.error(f"Failed to connect to browser: {str(e)}")
        return None, None

def ask_question(tab, question, timeout=30):
    """Send question to the AI interface and get response"""
    try:
        # Selectors
        input_selector = 'rich-textarea > div > p'
        send_button_selector = 'div[class*="send-button-container"] > button'
        response_selector = 'message-content[class*="model-response-text"]'

        # Get current number of responses
        count_expr = f"document.querySelectorAll('{response_selector}').length"
        result = tab.call_method("Runtime.evaluate", expression=count_expr, returnByValue=True)
        
        # Check if the result has the expected structure
        if 'result' not in result or 'value' not in result['result']:
            raise ValueError(f"Failed to get response count. Result: {result}")
        
        num_responses = result['result']['value']

        # Set the input text
        input_expr = f"document.querySelector('{input_selector}').textContent = `{question.replace('`', '\\`')}`;"
        tab.call_method("Runtime.evaluate", expression=input_expr)

        # Small delay to simulate typing
        time.sleep(1)

        # Click send button
        click_expr = f"document.querySelector('{send_button_selector}').click();"
        tab.call_method("Runtime.evaluate", expression=click_expr)

        # Wait for new response to appear
        start_time = time.time()
        current_num = num_responses
        
        # Create a progress bar for waiting
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        while time.time() - start_time < timeout:
            elapsed = time.time() - start_time
            progress = min(elapsed / timeout, 1.0)
            progress_bar.progress(progress)
            status_text.text(f"Waiting for response... ({elapsed:.1f}s)")
            
            result = tab.call_method("Runtime.evaluate", expression=count_expr, returnByValue=True)
            if 'result' in result and 'value' in result['result']:
                current_num = result['result']['value']
                if current_num > num_responses:
                    break
            time.sleep(1)
        else:
            progress_bar.empty()
            status_text.empty()
            raise TimeoutError("Timeout waiting for response to appear.")

        progress_bar.empty()
        status_text.text("Response received, waiting for completion...")

        # Wait additional time for streaming to complete
        time.sleep(5)
        status_text.empty()

        # Get the latest response text
        index = current_num - 1
        response_expr = f"document.querySelectorAll('{response_selector}')[{index}].innerText"
        result = tab.call_method("Runtime.evaluate", expression=response_expr, returnByValue=True)
        
        if 'result' not in result or 'value' not in result['result']:
            raise ValueError(f"Failed to get response text. Result: {result}")
        
        response = result['result']['value']
        return response
        
    except Exception as e:
        st.error(f"Error asking question: {str(e)}")
        st.error(f"Traceback: {traceback.format_exc()}")
        return None

def disconnect_browser():
    """Disconnect from browser and clean up"""
    try:
        if st.session_state.tab:
            st.session_state.tab.stop()
        if st.session_state.browser and st.session_state.tab:
            st.session_state.browser.close_tab(st.session_state.tab)
        st.session_state.browser = None
        st.session_state.tab = None
        st.session_state.connected = False
    except Exception as e:
        st.error(f"Error disconnecting: {str(e)}")

# Streamlit UI
st.title("🤖 Gem PyChrome Chat Interface")
st.markdown("---")

# Connection status and controls
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    if st.session_state.connected:
        st.success("✅ Connected to Chrome browser")
    else:
        st.warning("⚠️ Not connected to browser")

with col2:
    if st.button("Connect", disabled=st.session_state.connected):
        with st.spinner("Connecting to browser..."):
            browser, tab = connect_to_browser()
            if browser and tab:
                st.session_state.browser = browser
                st.session_state.tab = tab
                st.session_state.connected = True
                st.success("Connected successfully!")
                st.rerun()

with col3:
    if st.button("Disconnect", disabled=not st.session_state.connected):
        disconnect_browser()
        st.success("Disconnected successfully!")
        st.rerun()

st.markdown("---")

# Chat interface
if st.session_state.connected:
    st.subheader("💬 Chat Interface")
    
    # Input form
    with st.form("chat_form", clear_on_submit=True):
        question = st.text_area(
            "Enter your question:",
            placeholder="Type your question here...",
            height=100,
            key="question_input"
        )
        
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            send_button = st.form_submit_button("🚀 Send", use_container_width=True)
        with col2:
            clear_button = st.form_submit_button("🗑️ Clear History", use_container_width=True)
    
    # Handle form submissions
    if send_button and question.strip():
        with st.spinner("Sending question and waiting for response..."):
            response = ask_question(st.session_state.tab, question.strip())
            if response:
                # Add to chat history
                st.session_state.chat_history.append({
                    "question": question.strip(),
                    "response": response,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                st.rerun()
    
    if clear_button:
        st.session_state.chat_history = []
        st.success("Chat history cleared!")
        st.rerun()
    
    # Display chat history
    if st.session_state.chat_history:
        st.subheader("📝 Chat History")
        
        for i, chat in enumerate(reversed(st.session_state.chat_history)):
            with st.expander(f"Q: {chat['question'][:50]}{'...' if len(chat['question']) > 50 else ''} ({chat['timestamp']})", expanded=(i == 0)):
                st.markdown("**Question:**")
                st.info(chat['question'])
                
                st.markdown("**Response:**")
                st.success(chat['response'])
    else:
        st.info("No chat history yet. Send a question to get started!")

else:
    st.info("Please connect to the Chrome browser first to start chatting.")

# Sidebar with information
with st.sidebar:
    st.header("ℹ️ Information")
    st.markdown("""
    **Requirements:**
    - Chrome browser running with debug port
    - Specific tab ID: `8D25B8EDED124ED7635252EF0F0E4217`
    - PyChrome library installed
    
    **How to use:**
    1. Start Chrome with debug port: `chrome --remote-debugging-port=9222`
    2. Navigate to the AI chat interface
    3. Click "Connect" button
    4. Enter your questions and click "Send"
    
    **Features:**
    - Real-time chat interface
    - Progress indicators
    - Chat history
    - Error handling
    - Connection management
    """)
    
    st.markdown("---")
    st.markdown("**Status:**")
    if st.session_state.connected:
        st.success("🟢 Connected")
        st.write(f"Chat history: {len(st.session_state.chat_history)} messages")
    else:
        st.error("🔴 Disconnected")

# Auto-cleanup on app shutdown
if st.session_state.connected:
    st.markdown("---")
    st.caption("💡 Remember to disconnect when done to free up resources.")
