"""
Grok Handler Module - Handles both Web UI and API streaming responses
"""
import streamlit as st
import asyncio
import threading
import datetime
import json
import os
import sys
from openai import OpenAI
from streamlit.runtime.scriptrunner import add_script_run_ctx

# Handle imports for both standalone and module usage
try:
    from chat_handlers.grok_streaming_chat import send_message_with_streaming, cleanup_connections, get_full_response
except ImportError:
    # When running standalone, add parent directory to path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from chat_handlers.grok_streaming_chat import send_message_with_streaming, cleanup_connections, get_full_response

TIMEOUT_SEC = 120

def start_thread(fn, *args, **kwargs):
    """Utility – start a daemon thread that can call Streamlit commands."""
    th = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    add_script_run_ctx(th)          # <- critical line
    th.start()
    return th

def clean_grok_response(text):
    """Remove UI artifacts and unwanted elements from Grok's response"""
    if not text:
        return text
    
    # List of artifacts to remove - including the specific ones mentioned in the issue
    remove_artifacts = [
        'How can Grok help?',
        'DeepSearch',
        'Think Grok 3',
        'Grok 4',
        'Upgrade to SuperGrok',
        'How can Grok help? DeepSearch Think Grok 3 Upgrade to SuperGrok',
        'markdown\nCopy\nEdit\n',
        'markdown\nCollapse\nWrap\nCopy\n',
        'markdown\n',
        'Copy\n',
        'Edit\n',
        'Collapse\n',
        'Wrap\n',
        'Copy',
        'Edit',
        'Collapse',
        'Wrap'
    ]
    
    # Clean the text - multiple passes to catch all variations
    cleaned_text = text
    
    # First pass: exact string replacements
    for artifact in remove_artifacts:
        cleaned_text = cleaned_text.replace(artifact, '')
    
    # Second pass: use regex for more aggressive cleaning
    import re
    
    # Remove "Think Grok 3" and "Grok 4" with various spacing and formatting
    cleaned_text = re.sub(r'\s*Think\s+Grok\s+3\s*', ' ', cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'\s*Grok\s+4\s*', ' ', cleaned_text, flags=re.IGNORECASE)
    
    # Remove other Grok UI artifacts with regex
    cleaned_text = re.sub(r'\s*How\s+can\s+Grok\s+help\?\s*', ' ', cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'\s*DeepSearch\s*', ' ', cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'\s*Upgrade\s+to\s+SuperGrok\s*', ' ', cleaned_text, flags=re.IGNORECASE)
    
    # Remove new Grok UI artifacts (query limits, social media references, etc.)
    cleaned_text = re.sub(r'\d+\s*𝕏\s*posts\s*\d+\s*web\s*pages\s*[\d.]+s.*?hours\.', '', cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'One\s+query\s+left\s+for\s+Grok\s*\d*\.?\s*Limit\s+resets\s+every\s+\d+\s+hours\.', '', cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'Query\s+limit\s+reached\s+for\s+Grok\s*\d*\.?\s*Limit\s+refreshes\s+in\s+\d+\s+minutes\.', '', cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'\d+\s*posts\s*\d+\s*web\s*pages\s*[\d.]+s', '', cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'\d+\s*𝕏\s*posts\s*\d+\s*web\s*pages\s*[\d.]+s', '', cleaned_text, flags=re.IGNORECASE)
    
    # Remove text fragments that appear at the end
    cleaned_text = re.sub(r'\s*this\s+text\s*$', '', cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'\s*text\s*$', '', cleaned_text, flags=re.IGNORECASE)
    
    # Remove markdown UI artifacts
    cleaned_text = re.sub(r'\s*markdown\s*', ' ', cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'\s*Copy\s*', ' ', cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'\s*Edit\s*', ' ', cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'\s*Collapse\s*', ' ', cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'\s*Wrap\s*', ' ', cleaned_text, flags=re.IGNORECASE)
    
    # Remove multiple consecutive spaces and newlines
    cleaned_text = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_text)  # Replace 3+ newlines with 2
    cleaned_text = re.sub(r' {2,}', ' ', cleaned_text)  # Replace multiple spaces with single space
    
    # Remove leading/trailing whitespace from each line
    lines = cleaned_text.split('\n')
    cleaned_lines = [line.strip() for line in lines]
    cleaned_text = '\n'.join(cleaned_lines)
    
    return cleaned_text.strip()

def log_qa_pair(question: str, webui_answer: str = None, api_answer: str = None, webui_question: str = None, api_question: str = None):
    """Log question/answer pair to individual chat session history file with both Web UI and API responses and raw questions"""
    try:
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "question": question,
            "model": "grok"
        }
        
        # Add raw questions sent to each service if available
        if webui_question:
            log_entry["webui_question"] = webui_question
        if api_question:
            log_entry["api_question"] = api_question
        
        # Add responses if available - clean them before logging
        if webui_answer:
            log_entry["webui_answer"] = clean_grok_response(webui_answer)
        if api_answer:
            log_entry["api_answer"] = clean_grok_response(api_answer)
        
        # Create individual log file for this specific conversation
        conversation_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        individual_log_file = os.path.join("logs/grok", f"chat_session_history_{conversation_timestamp}.json")
        
        # Write to individual conversation log file
        with open(individual_log_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False, indent=2))
        
        # Also append to the main session log file for backward compatibility
        with open(st.session_state.grok_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False, indent=2) + "\n")
            
    except Exception as e:
        st.error(f"Failed to log Grok Q&A pair: {str(e)}")

def start_concurrent_streaming(question):
    """Start Web UI and/or API streaming based on enabled checkboxes"""
    webui_enabled = st.session_state.get("enable_grok_webui", False)
    api_enabled = st.session_state.get("enable_grok_api", False)
    
    # Debug: Print checkbox states
    print(f"DEBUG: Grok WebUI enabled: {webui_enabled}, API enabled: {api_enabled}")
    
    if not webui_enabled and not api_enabled:
        print("DEBUG: Neither Grok WebUI nor API enabled, returning early")
        return  # Nothing to start
    
    st.session_state.grok_concurrent_streaming_active = True
    # Only clear streaming text if we're starting new streams, not if we already have responses
    if webui_enabled and not st.session_state.get("grok_response"):
        st.session_state.grok_webui_streaming_text = ""
    if api_enabled and not st.session_state.get("grok_api_response"):
        st.session_state.grok_api_streaming_text = ""
    st.session_state.grok_webui_stream_complete = not webui_enabled  # Mark as complete if not enabled
    st.session_state.grok_api_stream_complete = not api_enabled     # Mark as complete if not enabled
    st.session_state.grok_generating_response = webui_enabled
    st.session_state.grok_generating_api_response = api_enabled
    st.session_state.stop_streaming = False
    
    # Store question for logging when responses complete
    st.session_state.grok_pending_log_question = question.strip()
    
    # Start Web UI streaming thread only if enabled
    if webui_enabled:
        print("DEBUG: Starting Grok WebUI streaming worker")
        start_thread(webui_streaming_worker, question)
    else:
        print("DEBUG: Grok WebUI disabled, not starting WebUI worker")
    
    # Start API streaming thread only if enabled
    if api_enabled:
        print("DEBUG: Starting Grok API streaming worker")
        start_thread(api_streaming_worker, question)
    else:
        print("DEBUG: Grok API disabled, not starting API worker")

def webui_streaming_worker(question):
    """Worker thread for Web UI streaming using new chunk-based streaming - updates session state incrementally"""
    try:
        # Double-check that WebUI is enabled before proceeding
        if not st.session_state.get("enable_grok_webui", False):
            st.session_state.grok_webui_stream_complete = True
            st.session_state.grok_generating_response = False
            return
        
        # Store original prompt for logging
        original_prompt = question.strip()
        cleaned_prompt = 'Answer in clean raw markdown language without citations. ' + original_prompt + ". Wrap the entire response in a markdown code block to show the actual syntax"
        #cleaned_prompt = original_prompt
        # Store the Web UI question for logging
        st.session_state.grok_pending_log_webui_question = cleaned_prompt
        
        # Add to conversation history
        st.session_state.grok_conversation_history.append({"role": "user", "content": cleaned_prompt})
        
        full_response = ""
        response_started = False
        
        # Use the new chunk-based streaming function
        try:
            for chunk_info in send_message_with_streaming(cleaned_prompt, TIMEOUT_SEC):
                if st.session_state.stop_streaming:
                    print("🛑 Grok streaming stopped by user, cleaning up connections...")
                    # When stopped, preserve the current response and clean it
                    if full_response:
                        cleaned_partial_response = clean_grok_response(full_response)
                        st.session_state.grok_conversation_history.append({"role": "assistant", "content": cleaned_partial_response})
                        st.session_state.grok_response = cleaned_partial_response
                        # Update the streaming text to the cleaned version without cursor
                        st.session_state.grok_webui_streaming_text = cleaned_partial_response
                    
                    # Clean up connections when stopped to prevent stale connection issues
                    cleanup_connections()
                    break
                
                # Extract chunk content from the chunk_info dictionary
                chunk_content = chunk_info.get('chunk', '') if isinstance(chunk_info, dict) else str(chunk_info)
                
                if chunk_content:
                    response_started = True
                    if not full_response:
                        st.session_state.grok_webui_streaming_text = "🚀 Grok started typing..."
                    
                    # Handle first chunk (full response) vs incremental chunks
                    if chunk_info.get('is_first', False):
                        # First chunk contains the full response so far
                        full_response = chunk_content
                    else:
                        # Incremental chunks are added to the response
                        full_response += chunk_content
                    
                    # Clean the response and update UI display with cursor
                    cleaned_full_response = clean_grok_response(full_response)
                    st.session_state.grok_webui_streaming_text = cleaned_full_response + "▌"
                    
                    # Check if this is the final chunk
                    if chunk_info.get('is_final', False):
                        break
                    
        except Exception as e:
            print(f"❌ Grok streaming error: {str(e)}, cleaning up connections...")
            cleanup_connections()
            st.session_state.grok_webui_streaming_text = f"Grok streaming error: {str(e)}"
            st.session_state.grok_webui_stream_complete = True
            st.session_state.grok_generating_response = False
            return
        
        # After streaming is complete, get the final clean response from the page
        try:
            # Get the final clean response directly from the page
            final_clean_response = get_full_response(original_prompt)
            if final_clean_response:
                # Clean the final response
                cleaned_final_response = clean_grok_response(final_clean_response)
                st.session_state.grok_conversation_history.append({"role": "assistant", "content": cleaned_final_response})
                st.session_state.grok_response = cleaned_final_response
                # Replace the accumulated chunks with the final clean response
                st.session_state.grok_webui_streaming_text = cleaned_final_response
            elif full_response:
                # Fallback to accumulated response if get_full_response fails
                cleaned_final_response = clean_grok_response(full_response)
                st.session_state.grok_conversation_history.append({"role": "assistant", "content": cleaned_final_response})
                st.session_state.grok_response = cleaned_final_response
                st.session_state.grok_webui_streaming_text = cleaned_final_response
        except Exception as e:
            print(f"⚠️ Error getting final response, using accumulated: {str(e)}")
            if full_response:
                cleaned_final_response = clean_grok_response(full_response)
                st.session_state.grok_conversation_history.append({"role": "assistant", "content": cleaned_final_response})
                st.session_state.grok_response = cleaned_final_response
                st.session_state.grok_webui_streaming_text = cleaned_final_response
        
        st.session_state.grok_webui_stream_complete = True
        st.session_state.grok_generating_response = False
        
    except Exception as e:
        st.session_state.grok_webui_streaming_text = f"Grok Error: {str(e)}"
        st.session_state.grok_webui_stream_complete = True
        st.session_state.grok_generating_response = False

def api_streaming_worker(question):
    """Worker thread for API streaming using actual Grok API - updates session state incrementally"""
    try:
        # Double-check that API is enabled before proceeding
        if not st.session_state.get("enable_grok_api", False):
            st.session_state.grok_api_stream_complete = True
            st.session_state.grok_generating_api_response = False
            return
        
        # Check for API key
        import os
        api_key = os.getenv("XAI_API_KEY")
        if not api_key or api_key == "your_xai_api_key_here":
            st.session_state.grok_api_streaming_text = "❌ Grok API Error: XAI_API_KEY not found or not set in .env file. Please add your xAI API key."
            st.session_state.grok_api_stream_complete = True
            st.session_state.grok_generating_api_response = False
            return
        
        st.session_state.grok_api_streaming_text = "🚀 Grok API started typing..."
        
        # Store the API question for logging
        st.session_state.grok_pending_log_api_question = question
        
        # Add to separate API conversation history
        st.session_state.grok_api_conversation_history.append({"role": "user", "content": question})
        
        # Initialize OpenAI client for xAI Grok API
        from openai import OpenAI
        
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1"
        )
        
        # Prepare messages for API call
        messages = [
            {"role": "system", "content": "You are Grok, a helpful AI assistant created by xAI. Provide clear, informative, and engaging responses."},
            {"role": "user", "content": question}
        ]
        
        # Make streaming API call
        full_response = ""
        try:
            stream = client.chat.completions.create(
                model="grok-beta",  # Use the available Grok model
                messages=messages,
                stream=True,
                max_tokens=4000,
                temperature=0.7
            )
            
            for chunk in stream:
                if st.session_state.stop_streaming:
                    # When stopped, preserve the current response without cursor
                    if full_response:
                        st.session_state.grok_api_streaming_text = full_response
                        st.session_state.grok_api_response = full_response
                        # Add response to separate API conversation history
                        st.session_state.grok_api_conversation_history.append({"role": "assistant", "content": full_response})
                    break
                    
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    
                    # Update streaming text with cursor
                    st.session_state.grok_api_streaming_text = full_response + "▌"
                    
        except Exception as api_error:
            error_msg = str(api_error)
            if "401" in error_msg or "authentication" in error_msg.lower():
                st.session_state.grok_api_streaming_text = "❌ Grok API Error: Invalid API key. Please check your XAI_API_KEY in the .env file."
            elif "429" in error_msg or "rate limit" in error_msg.lower():
                st.session_state.grok_api_streaming_text = "❌ Grok API Error: Rate limit exceeded. Please try again later."
            elif "quota" in error_msg.lower() or "billing" in error_msg.lower():
                st.session_state.grok_api_streaming_text = "❌ Grok API Error: API quota exceeded or billing issue. Please check your xAI account."
            else:
                st.session_state.grok_api_streaming_text = f"❌ Grok API Error: {error_msg}"
            
            st.session_state.grok_api_stream_complete = True
            st.session_state.grok_generating_api_response = False
            return
        
        # Final update without cursor
        if full_response:
            st.session_state.grok_api_streaming_text = full_response
            st.session_state.grok_api_response = full_response
            
            # Add response to separate API conversation history
            st.session_state.grok_api_conversation_history.append({"role": "assistant", "content": full_response})
        else:
            st.session_state.grok_api_streaming_text = "❌ No response received from Grok API"
        
        st.session_state.grok_api_stream_complete = True
        st.session_state.grok_generating_api_response = False
        
    except Exception as e:
        st.session_state.grok_api_streaming_text = f"❌ Grok API Error: {str(e)}"
        st.session_state.grok_api_stream_complete = True
        st.session_state.grok_generating_api_response = False

def render_grok_responses():
    """Render the Grok response UI with tabs containing Web UI and API columns"""
    if not (st.session_state.transcription and not st.session_state.recording):
        return

    # Control buttons row - removed duplicate Stop All Streaming button since there's already one at the top level
    button_col1, button_col2 = st.columns([1, 1])
    
    # Session History button
    with button_col1:
        if st.button("📚 Session History", key="grok_history_button"):
            st.session_state.show_grok_history = not st.session_state.get("show_grok_history", False)
            st.rerun()

    # Show session history if toggled
    if st.session_state.get("show_grok_history", False):
        with st.expander("📚 Grok Web UI Session History", expanded=True):
            show_grok_session_history()

    # Determine which columns to show based on enabled checkboxes
    webui_enabled = st.session_state.get("enable_grok_webui", False)
    api_enabled = st.session_state.get("enable_grok_api", False)
    
    if webui_enabled and api_enabled:
        # Show both columns side-by-side
        col_web, col_api = st.columns(2)
        
        # Web UI pane
        with col_web:
            st.markdown('<div class="box-header">🌐 Web UI</div>', unsafe_allow_html=True)
            
            # Always prioritize showing existing content, whether streaming or not
            if st.session_state.grok_webui_streaming_text:
                # Show streaming text (live or preserved after stop)
                st.markdown(st.session_state.grok_webui_streaming_text)
            elif st.session_state.grok_response:
                # Show final response - text is already cleaned in the worker
                st.markdown(st.session_state.grok_response)
            elif st.session_state.grok_generating_response:
                st.info("Grok response will appear here…")
            else:
                st.info("Click **Get AI Response** to generate responses")

        # API pane
        with col_api:
            st.markdown('<div class="box-header">⚡ API</div>', unsafe_allow_html=True)
            
            # Always prioritize showing existing content, whether streaming or not
            if st.session_state.grok_api_streaming_text:
                # Show streaming text (live or preserved after stop)
                st.markdown(st.session_state.grok_api_streaming_text)
            elif st.session_state.grok_api_response:
                # Show final response when not streaming
                st.markdown(st.session_state.grok_api_response)
            elif st.session_state.grok_generating_api_response:
                st.info("Grok API response will appear here…")
            else:
                st.info("Grok API responses will appear here")
                
    elif webui_enabled:
        # Show only Web UI column (full width)
        st.markdown('<div class="box-header">🌐 Web UI</div>', unsafe_allow_html=True)
        
        # Always prioritize showing existing content, whether streaming or not
        if st.session_state.grok_webui_streaming_text:
            # Show streaming text (live or preserved after stop)
            st.markdown(st.session_state.grok_webui_streaming_text)
        elif st.session_state.grok_response:
            # Show final response - text is already cleaned in the worker
            st.markdown(st.session_state.grok_response)
        elif st.session_state.grok_generating_response:
            st.info("Grok response will appear here…")
        else:
            st.info("Click **Get AI Response** to generate responses")
            
    elif api_enabled:
        # Show only API column (full width)
        st.markdown('<div class="box-header">⚡ API</div>', unsafe_allow_html=True)
        
        # Always prioritize showing existing content, whether streaming or not
        if st.session_state.grok_api_streaming_text:
            # Show streaming text (live or preserved after stop)
            st.markdown(st.session_state.grok_api_streaming_text)
        elif st.session_state.grok_api_response:
            # Show final response when not streaming
            st.markdown(st.session_state.grok_api_response)
        elif st.session_state.grok_generating_api_response:
            st.info("Grok API response will appear here…")
        else:
            st.info("Grok API responses will appear here")
    else:
        # Neither enabled
        st.info("Enable WebUI and/or API checkboxes above to see Grok responses")

def handle_concurrent_streaming():
    """Handle auto-refresh and completion logic for concurrent streaming - now handled centrally in main app"""
    # This function is now a no-op since refresh logic is centralized in the main app
    pass

def load_grok_session_history():
    """Load Grok session history from individual log files"""
    try:
        grok_logs_dir = "logs/grok"
        if not os.path.exists(grok_logs_dir):
            return []
        
        history_files = []
        # Get all chat_session_history files
        for filename in os.listdir(grok_logs_dir):
            if filename.startswith("chat_session_history_") and filename.endswith(".json"):
                filepath = os.path.join(grok_logs_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        data["filename"] = filename
                        history_files.append(data)
                except Exception as e:
                    st.error(f"Error reading {filename}: {str(e)}")
        
        # Sort by timestamp (newest first)
        history_files.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return history_files
        
    except Exception as e:
        st.error(f"Error loading Grok session history: {str(e)}")
        return []

def show_grok_session_history():
    """Display Grok Web UI session history in a popup-style expander"""
    history = load_grok_session_history()
    
    if not history:
        st.info("No Grok session history found.")
        return
    
    st.subheader("📚 Grok Web UI Session History")
    st.write(f"Found {len(history)} conversation(s)")
    
    for i, entry in enumerate(history):
        timestamp = entry.get("timestamp", "Unknown")
        question = entry.get("question", "No question")
        webui_answer = entry.get("webui_answer", "No Web UI answer")
        model = entry.get("model", "grok")
        
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
            
            st.markdown(f"**🚀 Model:** {model}")
            
            if webui_answer and webui_answer != "No Web UI answer":
                st.markdown("**🚀 Grok Web UI Response:**")
                
                # Use the comprehensive cleaning function
                cleaned_answer = clean_grok_response(webui_answer)
                st.markdown(cleaned_answer)
            else:
                st.info("No Web UI response recorded")
            
            # Show API response if available
            api_answer = entry.get("api_answer")
            if api_answer:
                st.markdown("**⚡ Grok API Response:**")
                st.markdown(api_answer)

def handle_stopped_streaming():
    """Handle stopped streaming cleanup"""
    if st.session_state.stop_streaming and (st.session_state.grok_generating_response or st.session_state.grok_generating_api_response):
        st.session_state.grok_generating_response = False
        st.session_state.grok_generating_api_response = False
        st.session_state.stop_streaming = False
        st.session_state.manual_transcription = None  # Clear manual transcription if stopped
        st.info("🛑 Grok streaming stopped by user")

# Standalone CLI test functionality
class MockSessionState:
    """Mock session state for standalone testing"""
    def __init__(self):
        self.data = {}
        self.stop_streaming = False
        self.grok_webui_streaming_text = ""
        self.grok_response = ""
        self.grok_conversation_history = []
        self.grok_webui_stream_complete = False
        self.grok_generating_response = False
        
    def get(self, key, default=None):
        return getattr(self, key, default)
    
    def __setattr__(self, key, value):
        super().__setattr__(key, value)

def standalone_grok_test(question, timeout=120):
    """Standalone test function for Grok handler without Streamlit"""
    print("🤖 GROK HANDLER STANDALONE TEST")
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
        st.session_state.enable_grok_webui = True
        st.session_state.grok_conversation_history = []
        
        # Create logs directory if it doesn't exist
        os.makedirs("logs/grok", exist_ok=True)
        st.session_state.grok_log_file = "logs/grok/test_session.log"
        
        print("🔄 Starting Grok WebUI streaming test...")
        print("-" * 50)
        
        # Store original prompt for logging
        original_prompt = question.strip()
        cleaned_prompt = 'Answer in clean raw markdown language. ' + original_prompt + ". Wrap the entire response in a markdown code block to show the actual syntax"
        
        print(f"📤 Sending cleaned prompt: {cleaned_prompt[:100]}...")
        
        # Add to conversation history
        st.session_state.grok_conversation_history.append({"role": "user", "content": cleaned_prompt})
        
        full_response = ""
        response_started = False
        
        # Use the new chunk-based streaming function
        try:
            print("\n🔄 Streaming response:")
            print("-" * 50)
            
            for chunk_info in send_message_with_streaming(cleaned_prompt, timeout):
                # Extract chunk content from the chunk_info dictionary
                chunk_content = chunk_info.get('chunk', '')
                is_first = chunk_info.get('is_first', False)
                is_final = chunk_info.get('is_final', False)
                is_filtered_out = chunk_info.get('is_filtered_out', False)
                
                # Skip filtered out chunks
                if is_filtered_out:
                    continue
                
                if chunk_content or is_final:
                    response_started = True
                    
                    if is_first:
                        # First chunk contains the full response so far
                        full_response = chunk_content
                        print("🚀 Grok started typing...")
                        print(chunk_content, end='', flush=True)
                    elif not is_final:
                        # Incremental chunk - add to full response
                        full_response += chunk_content
                        # Print the incremental chunk for real-time feedback
                        print(chunk_content, end='', flush=True)
                    
                    # Handle final chunk
                    if is_final:
                        break
                    
        except Exception as e:
            print(f"\n❌ Grok streaming error: {str(e)}")
            return False
        
        # Store final response
        if full_response:
            st.session_state.grok_conversation_history.append({"role": "assistant", "content": full_response})
            st.session_state.grok_response = full_response
            
            print("\n" + "=" * 50)
            print(f"✅ STREAMING COMPLETE! Total response length: {len(full_response)} characters")
            
            # Log the Q&A pair
            try:
                log_qa_pair(
                    question=original_prompt,
                    webui_answer=full_response,
                    webui_question=cleaned_prompt
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
        print("❌ Usage: python chat_handlers/grok_handler.py \"Your question here\"")
        print("📝 Example: python chat_handlers/grok_handler.py \"What is artificial intelligence?\"")
        sys.exit(1)
    
    question = sys.argv[1]
    
    # Optional timeout parameter
    timeout = 120
    if len(sys.argv) > 2:
        try:
            timeout = int(sys.argv[2])
        except ValueError:
            print("⚠️  Invalid timeout value, using default 120 seconds")
    
    success = standalone_grok_test(question, timeout)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
