"""
Perplexity Handler Module - Handles Web UI streaming responses
"""
import streamlit as st
import asyncio
import threading
import datetime
import json
import os
import sys
import requests
from streamlit.runtime.scriptrunner import add_script_run_ctx

# Handle imports for both standalone and module usage
try:
    from chat_handlers.perplexity_streaming_chat import send_message_with_streaming, cleanup_connections
except ImportError:
    # When running standalone, add parent directory to path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from chat_handlers.perplexity_streaming_chat import send_message_with_streaming, cleanup_connections

TIMEOUT_SEC = 120

def start_thread(fn, *args, **kwargs):
    """Utility – start a daemon thread that can call Streamlit commands."""
    th = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    add_script_run_ctx(th)          # <- critical line
    th.start()
    return th

def clean_perplexity_response(text):
    """Return text as-is without any filtering or cleaning"""
    return text if text else text

def log_qa_pair(question: str, webui_answer: str = None, api_answer: str = None, webui_question: str = None, api_question: str = None):
    """Log question/answer pair to individual chat session history file with both Web UI and API responses"""
    try:
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "question": question,
            "model": "perplexity"
        }
        
        # Add raw questions sent to each service if available
        if webui_question:
            log_entry["webui_question"] = webui_question
        if api_question:
            log_entry["api_question"] = api_question
        
        # Add responses if available - clean Web UI response before logging
        if webui_answer:
            log_entry["webui_answer"] = clean_perplexity_response(webui_answer)
        if api_answer:
            log_entry["api_answer"] = api_answer  # API responses are usually cleaner
        
        # Create individual log file for this specific conversation
        conversation_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        individual_log_file = os.path.join("logs/perplexity", f"chat_session_history_{conversation_timestamp}.json")
        
        # Create logs directory if it doesn't exist
        os.makedirs("logs/perplexity", exist_ok=True)
        
        # Write to individual conversation log file
        with open(individual_log_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False, indent=2))
        
        # Also append to the main session log file for backward compatibility
        main_log_file = os.path.join("logs/perplexity", "session_history.log")
        with open(main_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False, indent=2) + "\n")
            
    except Exception as e:
        if 'st' in globals():
            st.error(f"Failed to log Perplexity Q&A pair: {str(e)}")
        else:
            print(f"Failed to log Perplexity Q&A pair: {str(e)}")

def start_concurrent_streaming(question):
    """Start Web UI and/or API streaming based on enabled checkboxes"""
    webui_enabled = st.session_state.get("enable_perplexity_webui", False)
    api_enabled = st.session_state.get("enable_perplexity_api", False)
    
    # Debug: Print checkbox states
    print(f"DEBUG: Perplexity WebUI enabled: {webui_enabled}, API enabled: {api_enabled}")
    
    if not webui_enabled and not api_enabled:
        print("DEBUG: Neither WebUI nor API enabled, returning early")
        return  # Nothing to start
    
    st.session_state.perplexity_concurrent_streaming_active = True
    st.session_state.perplexity_webui_streaming_text = ""
    st.session_state.perplexity_api_streaming_text = ""
    st.session_state.perplexity_webui_stream_complete = not webui_enabled  # Mark as complete if not enabled
    st.session_state.perplexity_api_stream_complete = not api_enabled     # Mark as complete if not enabled
    st.session_state.perplexity_generating_response = webui_enabled
    st.session_state.perplexity_generating_api_response = api_enabled
    st.session_state.stop_streaming = False
    
    # Store question for logging when responses complete
    st.session_state.perplexity_pending_log_question = question.strip()
    
    # Start Web UI streaming thread only if enabled
    if webui_enabled:
        print("DEBUG: Starting Perplexity WebUI streaming worker")
        start_thread(webui_streaming_worker, question)
    else:
        print("DEBUG: Perplexity WebUI disabled, not starting WebUI worker")
    
    # Start API streaming thread only if enabled
    if api_enabled:
        print("DEBUG: Starting Perplexity API streaming worker")
        start_thread(api_streaming_worker, question)
    else:
        print("DEBUG: Perplexity API disabled, not starting API worker")

def webui_streaming_worker(question):
    """Worker thread for Web UI streaming using direct streaming_chat - updates session state incrementally"""
    try:
        # Double-check that WebUI is enabled before proceeding
        if not st.session_state.get("enable_perplexity_webui", False):
            st.session_state.perplexity_webui_stream_complete = True
            st.session_state.perplexity_generating_response = False
            return
        
        # Store original prompt for logging
        original_prompt = question.strip()
        cleaned_prompt = 'Answer this question in clean raw markdown language : ' +original_prompt + ".  Wrapp the entire response in a markdown code block to show the actual syntax"
        
        # Store the Web UI question for logging
        st.session_state.perplexity_pending_log_webui_question = cleaned_prompt
        
        # Add to conversation history
        st.session_state.perplexity_conversation_history.append({"role": "user", "content": cleaned_prompt})
        
        full_response = ""
        response_started = False
        
        # Use the direct streaming function (synchronous generator)
        try:
            for chunk_info in send_message_with_streaming(cleaned_prompt, TIMEOUT_SEC):
                if st.session_state.stop_streaming:
                    print("🛑 Streaming stopped by user, cleaning up connections...")
                    cleanup_connections()
                    break
                
                # Extract chunk content from the chunk info dictionary
                chunk_content = chunk_info.get('chunk', '') if isinstance(chunk_info, dict) else str(chunk_info)
                
                if chunk_content:
                    response_started = True
                    if not full_response:
                        st.session_state.perplexity_webui_streaming_text = "🔍 Perplexity started typing..."
                    
                    # Handle first chunk (full response) vs incremental chunks
                    if chunk_info.get('is_first', False):
                        # First chunk contains the full response so far
                        full_response = chunk_content
                    else:
                        # Incremental chunks are added to the response
                        full_response += chunk_content
                    
                    # Update session state for UI display with cursor - no cleaning
                    st.session_state.perplexity_webui_streaming_text = full_response + "▌"
                    
                    # Check if this is the final chunk
                    if chunk_info.get('is_final', False):
                        break
                    
        except Exception as e:
            print(f"❌ Perplexity streaming error: {str(e)}, cleaning up connections...")
            cleanup_connections()
            st.session_state.perplexity_webui_streaming_text = f"Perplexity streaming error: {str(e)}"
            st.session_state.perplexity_webui_stream_complete = True
            st.session_state.perplexity_generating_response = False
            return
        
        # Store final response without cleaning - remove cursor
        if full_response:
            st.session_state.perplexity_conversation_history.append({"role": "assistant", "content": full_response})
            st.session_state.perplexity_response = full_response
            # Update the streaming text to the final version without cursor
            st.session_state.perplexity_webui_streaming_text = full_response
        
        st.session_state.perplexity_webui_stream_complete = True
        st.session_state.perplexity_generating_response = False
        
    except Exception as e:
        st.session_state.perplexity_webui_streaming_text = f"Perplexity Error: {str(e)}"
        st.session_state.perplexity_webui_stream_complete = True
        st.session_state.perplexity_generating_response = False

def api_streaming_worker(question):
    """Worker thread for API streaming - updates session state incrementally"""
    try:
        # Double-check that API is enabled before proceeding
        if not st.session_state.get("enable_perplexity_api", False):
            st.session_state.perplexity_api_stream_complete = True
            st.session_state.perplexity_generating_api_response = False
            return
        
        # Store the API question for logging
        st.session_state.perplexity_pending_log_api_question = question
        
        # Add to separate API conversation history
        st.session_state.perplexity_api_conversation_history.append({"role": "user", "content": question})
        
        # Use separate API conversation history
        messages = st.session_state.perplexity_api_conversation_history
        
        full_response = ""
        
        # Get API key from environment - let it fail naturally if missing
        api_key = os.getenv("PERPLEXITY_API_KEY")
        
        # Perplexity API endpoint
        url = "https://api.perplexity.ai/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",  # Perplexity's online model
            "messages": messages,
            "stream": True,
            "max_tokens": 4000,
            "temperature": 0.2
        }
        
        st.session_state.perplexity_api_streaming_text = "🔍 Perplexity API started typing..."
        
        try:
            # Make streaming request
            response = requests.post(url, headers=headers, json=payload, stream=True)
            response.raise_for_status()
            
            for line in response.iter_lines():
                if st.session_state.stop_streaming:
                    break
                
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix
                        if data.strip() == '[DONE]':
                            break
                        
                        try:
                            chunk_data = json.loads(data)
                            if 'choices' in chunk_data and len(chunk_data['choices']) > 0:
                                delta = chunk_data['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    full_response += content
                                    # Update session state with cursor
                                    st.session_state.perplexity_api_streaming_text = full_response + "▌"
                        except json.JSONDecodeError:
                            continue  # Skip malformed JSON
            
            # Final update without cursor
            st.session_state.perplexity_api_streaming_text = full_response
            st.session_state.perplexity_api_response = full_response
            
            # Add response to separate API conversation history
            if full_response:
                st.session_state.perplexity_api_conversation_history.append({"role": "assistant", "content": full_response})
            
        except requests.exceptions.RequestException as e:
            import traceback
            error_msg = traceback.format_exc()
            st.session_state.perplexity_api_streaming_text = error_msg
            print(f"DEBUG: {error_msg}")
        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()
            st.session_state.perplexity_api_streaming_text = error_msg
            print(f"DEBUG: {error_msg}")
        
        st.session_state.perplexity_api_stream_complete = True
        st.session_state.perplexity_generating_api_response = False
        
    except Exception as e:
        st.session_state.perplexity_api_streaming_text = f"Perplexity API Error: {str(e)}"
        st.session_state.perplexity_api_stream_complete = True
        st.session_state.perplexity_generating_api_response = False

def render_perplexity_responses():
    """Render the Perplexity response UI with two-column layout"""
    if not (st.session_state.transcription and not st.session_state.recording):
        return

    # Show generating status
    if st.session_state.perplexity_generating_response or st.session_state.perplexity_generating_api_response:
        st.info("🔄 Generating Perplexity response...")

    # Control buttons row
    button_col1, button_col2 = st.columns([1, 1])
    
    # Stop button for streaming
    with button_col1:
        if st.session_state.perplexity_concurrent_streaming_active:
            if st.button("🛑 Stop Streaming", key="perplexity_stop_streaming"):
                st.session_state.stop_streaming = True
                st.session_state.perplexity_concurrent_streaming_active = False
                st.session_state.perplexity_generating_response = False
                st.session_state.perplexity_generating_api_response = False
                st.rerun()
    
    # Session History button
    with button_col2:
        if st.button("📚 Session History", key="perplexity_history_button"):
            st.session_state.show_perplexity_history = not st.session_state.get("show_perplexity_history", False)
            st.rerun()

    # Show session history if toggled
    if st.session_state.get("show_perplexity_history", False):
        with st.expander("📚 Perplexity Session History", expanded=True):
            show_perplexity_session_history()

    # Dynamic layout based on enabled checkboxes
    webui_enabled = st.session_state.get("enable_perplexity_webui", False)
    api_enabled = st.session_state.get("enable_perplexity_api", False)
    
    if webui_enabled or api_enabled:
        # If only API is enabled, show single column for API
        if api_enabled and not webui_enabled:
            st.markdown('<div class="box-header">API</div>', unsafe_allow_html=True)
            
            # Check if we have any API response content to display
            has_api_streaming_content = st.session_state.perplexity_api_streaming_text and st.session_state.perplexity_api_streaming_text.strip()
            has_api_final_response = st.session_state.perplexity_api_response and st.session_state.perplexity_api_response.strip()
            
            # Debug: Print API streaming states
            print(f"DEBUG API: concurrent_active={st.session_state.perplexity_concurrent_streaming_active}, generating_api={st.session_state.perplexity_generating_api_response}")
            print(f"DEBUG API: has_streaming_content={bool(has_api_streaming_content)}, has_final_response={bool(has_api_final_response)}")
            
            if st.session_state.perplexity_generating_api_response:
                # Show live API streaming updates
                if has_api_streaming_content:
                    with st.container():
                        st.markdown(st.session_state.perplexity_api_streaming_text)
                else:
                    st.info("🔄 Starting API response...")
            elif has_api_streaming_content:
                # Show API content (including errors) when not actively generating
                # Check if it's an error message
                if ("error" in st.session_state.perplexity_api_streaming_text.lower() or 
                    "❌" in st.session_state.perplexity_api_streaming_text):
                    st.error(st.session_state.perplexity_api_streaming_text)
                else:
                    with st.container():
                        st.markdown(st.session_state.perplexity_api_streaming_text)
            elif has_api_final_response:
                # Show final API response when not streaming
                with st.container():
                    st.markdown(st.session_state.perplexity_api_response)
            else:
                st.info("🔄 Waiting for API response...")
        
        # If only WebUI is enabled, show single column for WebUI
        elif webui_enabled and not api_enabled:
            st.markdown('<div class="box-header">Web UI</div>', unsafe_allow_html=True)
            
            # Check if we have any response content to display
            has_streaming_content = st.session_state.perplexity_webui_streaming_text and st.session_state.perplexity_webui_streaming_text.strip()
            has_final_response = st.session_state.perplexity_response and st.session_state.perplexity_response.strip()
            
            if st.session_state.perplexity_concurrent_streaming_active and st.session_state.perplexity_generating_response:
                # Show live streaming updates - text is already cleaned in the worker
                if has_streaming_content:
                    # Use a container with proper styling for better markdown rendering
                    with st.container():
                        st.markdown(st.session_state.perplexity_webui_streaming_text)
                else:
                    st.info("🔄 Starting Web UI response...")
            elif has_final_response:
                # Show final response when not streaming - text is already cleaned in the worker
                with st.container():
                    st.markdown(st.session_state.perplexity_response)
            else:
                st.info("Click **Get AI Response** to generate Web UI response")
        
        # If both are enabled, show two-column layout
        else:
            col1, col2 = st.columns(2)
            
            # Web UI Column
            with col1:
                st.markdown('<div class="box-header">Web UI</div>', unsafe_allow_html=True)
                
                if webui_enabled:
                    # Check if we have any response content to display
                    has_streaming_content = st.session_state.perplexity_webui_streaming_text and st.session_state.perplexity_webui_streaming_text.strip()
                    has_final_response = st.session_state.perplexity_response and st.session_state.perplexity_response.strip()
                    
                    if st.session_state.perplexity_concurrent_streaming_active and st.session_state.perplexity_generating_response:
                        # Show live streaming updates - text is already cleaned in the worker
                        if has_streaming_content:
                            with st.container():
                                st.markdown(st.session_state.perplexity_webui_streaming_text)
                        else:
                            st.info("🔄 Starting Web UI response...")
                    elif has_final_response:
                        # Show final response when not streaming - text is already cleaned in the worker
                        with st.container():
                            st.markdown(st.session_state.perplexity_response)
                    else:
                        st.info("Click **Get AI Response** to generate Web UI response")
                else:
                    st.info("Web UI disabled")
            
            # API Column
            with col2:
                st.markdown('<div class="box-header">API</div>', unsafe_allow_html=True)
                
                if api_enabled:
                    # Check if we have any API response content to display
                    has_api_streaming_content = st.session_state.perplexity_api_streaming_text and st.session_state.perplexity_api_streaming_text.strip()
                    has_api_final_response = st.session_state.perplexity_api_response and st.session_state.perplexity_api_response.strip()
                    
                    # Debug: Print API streaming states
                    print(f"DEBUG API: concurrent_active={st.session_state.perplexity_concurrent_streaming_active}, generating_api={st.session_state.perplexity_generating_api_response}")
                    print(f"DEBUG API: has_streaming_content={bool(has_api_streaming_content)}, has_final_response={bool(has_api_final_response)}")
                    
                    if st.session_state.perplexity_generating_api_response:
                        # Show live API streaming updates
                        if has_api_streaming_content:
                            with st.container():
                                st.markdown(st.session_state.perplexity_api_streaming_text)
                        else:
                            st.info("🔄 Starting API response...")
                    elif has_api_streaming_content:
                        # Show API content (including errors) when not actively generating
                        # Check if it's an error message
                        if ("error" in st.session_state.perplexity_api_streaming_text.lower() or 
                            "❌" in st.session_state.perplexity_api_streaming_text):
                            st.error(st.session_state.perplexity_api_streaming_text)
                        else:
                            with st.container():
                                st.markdown(st.session_state.perplexity_api_streaming_text)
                    elif has_api_final_response:
                        # Show final API response when not streaming
                        with st.container():
                            st.markdown(st.session_state.perplexity_api_response)
                    else:
                        st.info("🔄 Waiting for API response...")
                else:
                    st.info("API disabled")
    else:
        # Neither WebUI nor API enabled
        st.info("Enable Perplexity Web UI or API checkbox above to see responses")

def handle_concurrent_streaming():
    """Handle auto-refresh and completion logic for concurrent streaming - now handled centrally in main app"""
    # This function is now a no-op since refresh logic is centralized in the main app
    pass

def load_perplexity_session_history():
    """Load Perplexity session history from individual log files"""
    try:
        perplexity_logs_dir = "logs/perplexity"
        if not os.path.exists(perplexity_logs_dir):
            return []
        
        history_files = []
        # Get all chat_session_history files
        for filename in os.listdir(perplexity_logs_dir):
            if filename.startswith("chat_session_history_") and filename.endswith(".json"):
                filepath = os.path.join(perplexity_logs_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        data["filename"] = filename
                        history_files.append(data)
                except Exception as e:
                    if 'st' in globals():
                        st.error(f"Error reading {filename}: {str(e)}")
                    else:
                        print(f"Error reading {filename}: {str(e)}")
        
        # Sort by timestamp (newest first)
        history_files.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return history_files
        
    except Exception as e:
        if 'st' in globals():
            st.error(f"Error loading Perplexity session history: {str(e)}")
        else:
            print(f"Error loading Perplexity session history: {str(e)}")
        return []

def show_perplexity_session_history():
    """Display Perplexity session history in a popup-style expander"""
    history = load_perplexity_session_history()
    
    if not history:
        st.info("No Perplexity session history found.")
        return
    
    st.subheader("📚 Perplexity Session History")
    st.write(f"Found {len(history)} conversation(s)")
    
    for i, entry in enumerate(history):
        timestamp = entry.get("timestamp", "Unknown")
        question = entry.get("question", "No question")
        webui_answer = entry.get("webui_answer", "No answer")
        model = entry.get("model", "perplexity")
        
        # Format timestamp for display
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            formatted_time = timestamp
        
        # Create an expander for each conversation
        with st.expander(f"🕒 {formatted_time} - {question[:50]}{'...' if len(question) > 50 else ''}"):
            st.markdown("**❓ Question:**")
            st.markdown(question)
            
            st.markdown(f"**🔍 Model:** {model}")
            
            if webui_answer and webui_answer != "No answer":
                st.markdown("**🔍 Perplexity Response:**")
                
                # Use the comprehensive cleaning function
                cleaned_answer = clean_perplexity_response(webui_answer)
                st.markdown(cleaned_answer)
            else:
                st.info("No response recorded")

def handle_stopped_streaming():
    """Handle stopped streaming cleanup"""
    if st.session_state.stop_streaming and st.session_state.perplexity_generating_response:
        st.session_state.perplexity_generating_response = False
        st.session_state.stop_streaming = False
        st.session_state.manual_transcription = None  # Clear manual transcription if stopped
        st.info("🛑 Perplexity streaming stopped by user")

# Standalone CLI test functionality
class MockSessionState:
    """Mock session state for standalone testing"""
    def __init__(self):
        self.data = {}
        self.stop_streaming = False
        self.perplexity_webui_streaming_text = ""
        self.perplexity_response = ""
        self.perplexity_conversation_history = []
        self.perplexity_webui_stream_complete = False
        self.perplexity_generating_response = False
        
    def get(self, key, default=None):
        return getattr(self, key, default)
    
    def __setattr__(self, key, value):
        super().__setattr__(key, value)

def standalone_perplexity_test(question, timeout=120):
    """Standalone test function for Perplexity handler without Streamlit"""
    print("🔍 PERPLEXITY HANDLER STANDALONE TEST")
    print("=" * 50)
    print(f"❓ Question: {question}")
    print("=" * 50)
    
    # Create mock session state
    mock_st = MockSessionState()
    
    # Mock the streamlit module for standalone testing
    import sys
    from types import ModuleType
    
    # Create a mock streamlit module
    mock_streamlit = ModuleType('streamlit')
    mock_streamlit.session_state = mock_st
    
    # Replace the imported st with our mock
    global st
    original_st = st
    st = mock_streamlit
    
    try:
        # Enable WebUI for testing
        st.session_state.enable_perplexity_webui = True
        st.session_state.perplexity_conversation_history = []
        
        # Create logs directory if it doesn't exist
        os.makedirs("logs/perplexity", exist_ok=True)
        
        print("🔄 Starting Perplexity WebUI streaming test...")
        print("-" * 50)
        
        # Store original prompt for logging
        original_prompt = question.strip()
        cleaned_prompt = 'Answer in clean raw markdown language. ' +original_prompt + ".  Wrapp the entire response in a markdown code block to show the actual syntax"
        
        print(f"📤 Sending prompt: {cleaned_prompt}")
        
        # Add to conversation history
        st.session_state.perplexity_conversation_history.append({"role": "user", "content": cleaned_prompt})
        
        full_response = ""
        response_started = False
        
        # Use the direct streaming function (synchronous generator)
        try:
            print("\n🔄 Streaming response:")
            print("-" * 50)
            
            for chunk_info in send_message_with_streaming(cleaned_prompt, timeout):
                # Extract chunk content from the chunk info dictionary
                chunk_content = chunk_info.get('chunk', '') if isinstance(chunk_info, dict) else str(chunk_info)
                
                if chunk_content:
                    response_started = True
                    if not full_response:
                        print("🔍 Perplexity started typing...")
                    
                    # Handle first chunk (full response) vs incremental chunks
                    if chunk_info.get('is_first', False):
                        # First chunk contains the full response so far
                        full_response = chunk_content
                        print(f"\n📦 First chunk received ({len(chunk_content)} chars)")
                        print(chunk_content, end='', flush=True)
                    else:
                        # Incremental chunks are added to the response
                        full_response += chunk_content
                        # Print the incremental chunk for real-time feedback
                        print(chunk_content, end='', flush=True)
                    
                    # Check if this is the final chunk
                    if chunk_info.get('is_final', False):
                        print(f"\n📦 Final chunk received - streaming complete")
                        break
                    
        except Exception as e:
            print(f"\n❌ Perplexity streaming error: {str(e)}")
            return False
        
        # Store final response
        if full_response:
            cleaned_final_response = clean_perplexity_response(full_response)
            st.session_state.perplexity_conversation_history.append({"role": "assistant", "content": cleaned_final_response})
            st.session_state.perplexity_response = cleaned_final_response
            
            print("\n" + "=" * 50)
            print(f"✅ STREAMING COMPLETE! Total response length: {len(full_response)} characters")
            print(f"✅ Cleaned response length: {len(cleaned_final_response)} characters")
            
            # Log the Q&A pair
            try:
                log_qa_pair(
                    question=original_prompt,
                    webui_answer=full_response,
                    webui_question=original_prompt
                )
                print("📝 Response logged successfully")
            except Exception as e:
                print(f"⚠️  Logging failed: {str(e)}")
            
            return True
        else:
            print("\n❌ No response received")
            return False
            
    except Exception as e:
        print(f"❌ Error in standalone test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Restore original streamlit module
        st = original_st
        print("\n✅ Standalone test completed!")

def main():
    """Main function for CLI usage"""
    import sys
    
    if len(sys.argv) < 2:
        print("❌ Usage: python chat_handlers/perplexity_handler.py \"Your question here\"")
        print("📝 Example: python chat_handlers/perplexity_handler.py \"What is artificial intelligence?\"")
        sys.exit(1)
    
    question = sys.argv[1]
    
    # Optional timeout parameter
    timeout = 120
    if len(sys.argv) > 2:
        try:
            timeout = int(sys.argv[2])
        except ValueError:
            print("⚠️  Invalid timeout value, using default 120 seconds")
    
    success = standalone_perplexity_test(question, timeout)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
