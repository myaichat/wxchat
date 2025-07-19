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
from streamlit.runtime.scriptrunner import add_script_run_ctx

# Handle imports for both standalone and module usage
try:
    from chat_handlers.perplexity_streaming_chat import send_message_with_streaming
except ImportError:
    # When running standalone, add parent directory to path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from chat_handlers.perplexity_streaming_chat import send_message_with_streaming

TIMEOUT_SEC = 120

def start_thread(fn, *args, **kwargs):
    """Utility – start a daemon thread that can call Streamlit commands."""
    th = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    add_script_run_ctx(th)          # <- critical line
    th.start()
    return th

def clean_perplexity_response(text):
    """Remove UI artifacts and unwanted elements from Perplexity's response"""
    if not text:
        return text
    
    # List of artifacts to remove - Perplexity-specific UI elements
    remove_artifacts = [
        'Ask anything...',
        'Search',
        'Pro',
        'Sources',
        'Related',
        'Follow-up',
        'Share',
        'Copy',
        'Regenerate',
        'Ask follow-up',
        'View sources',
        'Pro Search',
        'Focus',
        'All',
        'Academic',
        'Writing',
        'Wolfram|Alpha',
        'YouTube',
        'Reddit',
        'News',
        'Answer',
        'Ask a follow-up…',
        'American English'
    ]
    
    # Clean the text - multiple passes to catch all variations
    cleaned_text = text
    
    # First pass: exact string replacements
    for artifact in remove_artifacts:
        cleaned_text = cleaned_text.replace(artifact, '')
    
    # Second pass: use regex for more aggressive cleaning
    import re
    
    # Remove Perplexity UI artifacts with regex
    cleaned_text = re.sub(r'\s*Ask\s+anything\.\.\.\s*', ' ', cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'\s*Pro\s+Search\s*', ' ', cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'\s*Ask\s+a\s+follow-up\s*', ' ', cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'\s*American\s+English\s*', ' ', cleaned_text, flags=re.IGNORECASE)
    
    # Remove source indicators and references
    cleaned_text = re.sub(r'Sources\s*·\s*', '', cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'·\s*[^\n]*\.(org|com|gov|edu|uk)\s*', '', cleaned_text, flags=re.IGNORECASE)
    
    # Remove multiple consecutive spaces and newlines
    cleaned_text = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_text)  # Replace 3+ newlines with 2
    cleaned_text = re.sub(r' {2,}', ' ', cleaned_text)  # Replace multiple spaces with single space
    
    # Remove leading/trailing whitespace from each line
    lines = cleaned_text.split('\n')
    cleaned_lines = [line.strip() for line in lines]
    cleaned_text = '\n'.join(cleaned_lines)
    
    return cleaned_text.strip()

def log_qa_pair(question: str, webui_answer: str = None, webui_question: str = None):
    """Log question/answer pair to individual chat session history file"""
    try:
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "question": question,
            "model": "perplexity"
        }
        
        # Add raw question sent to service if available
        if webui_question:
            log_entry["webui_question"] = webui_question
        
        # Add response if available - clean it before logging
        if webui_answer:
            log_entry["webui_answer"] = clean_perplexity_response(webui_answer)
        
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
    """Start Web UI streaming"""
    webui_enabled = st.session_state.get("enable_perplexity_webui", False)
    
    # Debug: Print checkbox state
    print(f"DEBUG: Perplexity WebUI enabled: {webui_enabled}")
    
    if not webui_enabled:
        print("DEBUG: Perplexity WebUI not enabled, returning early")
        return  # Nothing to start
    
    st.session_state.perplexity_concurrent_streaming_active = True
    st.session_state.perplexity_webui_streaming_text = ""
    st.session_state.perplexity_webui_stream_complete = False
    st.session_state.perplexity_generating_response = True
    st.session_state.stop_streaming = False
    
    # Store question for logging when response completes
    st.session_state.perplexity_pending_log_question = question.strip()
    
    # Start Web UI streaming thread
    print("DEBUG: Starting Perplexity WebUI streaming worker")
    start_thread(webui_streaming_worker, question)

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
        cleaned_prompt = 'Answer in clean raw markdown language. ' + original_prompt + ". Wrap the entire response in a markdown code block to show the actual syntax"
        
        # Store the Web UI question for logging
        st.session_state.perplexity_pending_log_webui_question = cleaned_prompt
        
        # Add to conversation history
        st.session_state.perplexity_conversation_history.append({"role": "user", "content": cleaned_prompt})
        
        full_response = ""
        response_started = False
        
        # Use the direct streaming function (synchronous generator)
        try:
            for chunk in send_message_with_streaming(cleaned_prompt, TIMEOUT_SEC):
                if st.session_state.stop_streaming:
                    break
                
                # The chunk is raw text content from the streaming function
                if chunk:
                    response_started = True
                    if not full_response:
                        st.session_state.perplexity_webui_streaming_text = "🔍 Perplexity started typing..."
                    
                    # The chunk from send_message_with_streaming is actually a delta (new content only)
                    # Add the new chunk to our response
                    full_response += chunk
                    
                    # Clean the response more aggressively during streaming
                    # Apply cleaning to the full response to catch artifacts that span chunks
                    cleaned_full_response = clean_perplexity_response(full_response)
                    
                    # Update session state for UI display with cursor
                    st.session_state.perplexity_webui_streaming_text = cleaned_full_response + "▌"
                    
        except Exception as e:
            st.session_state.perplexity_webui_streaming_text = f"Perplexity streaming error: {str(e)}"
            st.session_state.perplexity_webui_stream_complete = True
            st.session_state.perplexity_generating_response = False
            return
        
        # Store final response - clean it before storing and remove cursor
        if full_response:
            cleaned_final_response = clean_perplexity_response(full_response)
            st.session_state.perplexity_conversation_history.append({"role": "assistant", "content": cleaned_final_response})
            st.session_state.perplexity_response = cleaned_final_response
            # Update the streaming text to the final cleaned version without cursor
            st.session_state.perplexity_webui_streaming_text = cleaned_final_response
        
        st.session_state.perplexity_webui_stream_complete = True
        st.session_state.perplexity_generating_response = False
        
    except Exception as e:
        st.session_state.perplexity_webui_streaming_text = f"Perplexity Error: {str(e)}"
        st.session_state.perplexity_webui_stream_complete = True
        st.session_state.perplexity_generating_response = False

def render_perplexity_responses():
    """Render the Perplexity response UI"""
    if not (st.session_state.transcription and not st.session_state.recording):
        return

    # Show generating status
    if st.session_state.perplexity_generating_response:
        st.info("🔄 Generating Perplexity response...")

    # Control buttons row
    button_col1, button_col2, button_col3 = st.columns([1, 1, 2])
    
    # Stop button for streaming
    with button_col1:
        if st.session_state.perplexity_concurrent_streaming_active:
            if st.button("🛑 Stop Streaming", key="perplexity_stop_streaming"):
                st.session_state.stop_streaming = True
                st.session_state.perplexity_concurrent_streaming_active = False
                st.session_state.perplexity_generating_response = False
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

    # Determine if WebUI is enabled
    webui_enabled = st.session_state.get("enable_perplexity_webui", False)
    
    if webui_enabled:
        # Show Web UI response
        st.markdown('<div class="box-header">🔍 Perplexity</div>', unsafe_allow_html=True)
        
        if st.session_state.perplexity_concurrent_streaming_active:
            # Show live streaming updates - text is already cleaned in the worker
            if st.session_state.perplexity_webui_streaming_text:
                st.markdown(st.session_state.perplexity_webui_streaming_text)
            else:
                st.info("Perplexity response will appear here…")
        elif st.session_state.perplexity_response and not st.session_state.perplexity_concurrent_streaming_active:
            # Show final response when not streaming - text is already cleaned in the worker
            st.markdown(st.session_state.perplexity_response)
        elif st.session_state.perplexity_generating_response:
            st.info("Perplexity response will appear here…")
        else:
            st.info("Click **Get AI Response** to generate responses")
    else:
        # WebUI not enabled
        st.info("Enable Perplexity WebUI checkbox above to see responses")

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
        
        print(f"📤 Sending prompt: {original_prompt}")
        
        # Add to conversation history
        st.session_state.perplexity_conversation_history.append({"role": "user", "content": original_prompt})
        
        full_response = ""
        response_started = False
        
        # Use the direct streaming function (synchronous generator)
        try:
            print("\n🔄 Streaming response:")
            print("-" * 50)
            
            for chunk in send_message_with_streaming(original_prompt, timeout):
                if chunk:
                    response_started = True
                    if not full_response:
                        print("🔍 Perplexity started typing...")
                    
                    # Add the new chunk to our response
                    full_response += chunk
                    
                    # Print the chunk for real-time feedback
                    print(chunk, end='', flush=True)
                    
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
