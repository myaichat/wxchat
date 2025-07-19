import streamlit as st
import pychrome
import time
import traceback
import threading
from queue import Queue

# Initialize session state
if 'browser' not in st.session_state:
    st.session_state.browser = None
if 'tab' not in st.session_state:
    st.session_state.tab = None
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'streaming_response' not in st.session_state:
    st.session_state.streaming_response = ""
if 'is_streaming' not in st.session_state:
    st.session_state.is_streaming = False

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

def get_response_text(tab, response_selector, index):
    """Get the current text of a response element"""
    try:
        response_expr = f"document.querySelectorAll('{response_selector}')[{index}].innerText"
        result = tab.call_method("Runtime.evaluate", expression=response_expr, returnByValue=True)
        
        if 'result' in result and 'value' in result['result']:
            return result['result']['value']
        return ""
    except:
        return ""

def ask_question_streaming(tab, question, timeout=60):
    """Send question to the AI interface and stream the response"""
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
        
        # Wait for response to start
        while time.time() - start_time < 30:  # 30 second timeout for response to start
            result = tab.call_method("Runtime.evaluate", expression=count_expr, returnByValue=True)
            if 'result' in result and 'value' in result['result']:
                current_num = result['result']['value']
                if current_num > num_responses:
                    break
            time.sleep(0.5)
        else:
            raise TimeoutError("Timeout waiting for response to appear.")

        # Get the response index
        response_index = current_num - 1
        
        # Stream the response
        previous_text = ""
        last_change_time = time.time()
        stable_count = 0
        
        while time.time() - start_time < timeout:
            current_text = get_response_text(tab, response_selector, response_index)
            
            if current_text != previous_text:
                # Text has changed, yield the new content
                yield current_text
                previous_text = current_text
                last_change_time = time.time()
                stable_count = 0
            else:
                # Text hasn't changed
                stable_count += 1
                
                # If text has been stable for 3 seconds, consider it complete
                if time.time() - last_change_time > 3 and len(current_text) > 0:
                    break
                    
                # If we've had many stable checks and have some content, likely done
                if stable_count > 6 and len(current_text) > 50:
                    break
            
            time.sleep(0.5)
        
        # Final yield of complete response
        final_text = get_response_text(tab, response_selector, response_index)
        if final_text:
            yield final_text
            
    except Exception as e:
        yield f"Error: {str(e)}"

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
st.title("🤖 Gem PyChrome Streaming Chat Interface")
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
    st.subheader("💬 Streaming Chat Interface")
    
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
            send_button = st.form_submit_button("🚀 Send", use_container_width=True, disabled=st.session_state.is_streaming)
        with col2:
            clear_button = st.form_submit_button("🗑️ Clear History", use_container_width=True)
    
    # Handle form submissions
    if send_button and question.strip() and not st.session_state.is_streaming:
        st.session_state.is_streaming = True
        st.session_state.streaming_response = ""
        
        # Create containers for streaming response
        st.markdown("### 🔄 Live Response:")
        response_container = st.empty()
        status_container = st.empty()
        
        try:
            # Stream the response
            full_response = ""
            for chunk in ask_question_streaming(st.session_state.tab, question.strip()):
                full_response = chunk
                # Update the display with current response
                with response_container.container():
                    st.markdown("**Current Response:**")
                    st.info(full_response)
                
                # Update status
                status_container.text(f"Streaming... ({len(full_response)} characters)")
                
                # Small delay to make streaming visible
                time.sleep(0.1)
            
            # Final update
            status_container.success("✅ Response complete!")
            
            # Add to chat history
            if full_response and not full_response.startswith("Error:"):
                st.session_state.chat_history.append({
                    "question": question.strip(),
                    "response": full_response,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
            
        except Exception as e:
            st.error(f"Error during streaming: {str(e)}")
        finally:
            st.session_state.is_streaming = False
            time.sleep(2)  # Brief pause before allowing next question
            st.rerun()
    
    if clear_button:
        st.session_state.chat_history = []
        st.success("Chat history cleared!")
        st.rerun()
    
    # Show streaming status
    if st.session_state.is_streaming:
        st.warning("🔄 Currently streaming response... Please wait.")
    
    # Display chat history
    if st.session_state.chat_history:
        st.markdown("---")
        st.subheader("📝 Chat History")
        
        for i, chat in enumerate(reversed(st.session_state.chat_history)):
            with st.expander(f"Q: {chat['question'][:50]}{'...' if len(chat['question']) > 50 else ''} ({chat['timestamp']})", expanded=(i == 0)):
                st.markdown("**Question:**")
                st.info(chat['question'])
                
                st.markdown("**Response:**")
                st.success(chat['response'])
    else:
        if not st.session_state.is_streaming:
            st.info("No chat history yet. Send a question to get started!")

else:
    st.info("Please connect to the Chrome browser first to start chatting.")

# Sidebar with information
with st.sidebar:
    st.header("ℹ️ Information")
    st.markdown("""
    **Streaming Features:**
    - Real-time response display
    - Character count updates
    - Live streaming indicators
    - Automatic completion detection
    
    **Requirements:**
    - Chrome browser running with debug port
    - Specific tab ID: `8D25B8EDED124ED7635252EF0F0E4217`
    - PyChrome library installed
    
    **How to use:**
    1. Start Chrome with debug port: `chrome --remote-debugging-port=9222`
    2. Navigate to the AI chat interface
    3. Click "Connect" button
    4. Enter your questions and click "Send"
    5. Watch the response stream in real-time!
    
    **Features:**
    - 🔄 Real-time streaming
    - 📊 Progress indicators
    - 📝 Chat history
    - ⚠️ Error handling
    - 🔗 Connection management
    """)
    
    st.markdown("---")
    st.markdown("**Status:**")
    if st.session_state.connected:
        st.success("🟢 Connected")
        if st.session_state.is_streaming:
            st.warning("🔄 Streaming...")
        else:
            st.info("💬 Ready for questions")
        st.write(f"Chat history: {len(st.session_state.chat_history)} messages")
    else:
        st.error("🔴 Disconnected")

# Auto-cleanup on app shutdown
if st.session_state.connected:
    st.markdown("---")
    st.caption("💡 Remember to disconnect when done to free up resources.")
