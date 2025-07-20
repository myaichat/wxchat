"""
ChatGPT Handler Module - Handles both Web UI and API streaming responses
"""
import streamlit as st
import asyncio
import threading
import datetime
import json
import os
from openai import OpenAI
from streamlit.runtime.scriptrunner import add_script_run_ctx
from chat_handlers.chatgpt_streaming_chat import send_message_with_streaming

TIMEOUT_SEC = 60

def start_thread(fn, *args, **kwargs):
    """Utility – start a daemon thread that can call Streamlit commands."""
    th = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    add_script_run_ctx(th)          # <- critical line
    th.start()
    return th

def log_qa_pair(question: str, webui_answer: str = None, api_answer: str = None, webui_question: str = None, api_question: str = None):
    """Log question/answer pair to individual chat session history file with both Web UI and API responses and raw questions"""
    try:
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "question": question,
            "model": st.session_state.selected_model
        }
        
        # Add raw questions sent to each service if available
        if webui_question:
            log_entry["webui_question"] = webui_question
        if api_question:
            log_entry["api_question"] = api_question
        
        # Add responses if available
        if webui_answer:
            log_entry["webui_answer"] = webui_answer
        if api_answer:
            log_entry["api_answer"] = api_answer
        
        # Create individual log file for this specific conversation
        conversation_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        individual_log_file = os.path.join("logs/chatgpt", f"chat_session_history_{conversation_timestamp}.json")
        
        # Write to individual conversation log file
        with open(individual_log_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False, indent=2))
        
        # Also append to the main session log file for backward compatibility
        with open(st.session_state.chatgpt_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False, indent=2) + "\n")
            
    except Exception as e:
        st.error(f"Failed to log Q&A pair: {str(e)}")

def start_concurrent_streaming(question):
    """Start Web UI and/or API streaming based on enabled checkboxes"""
    webui_enabled = st.session_state.get("enable_chatgpt_webui", False)
    api_enabled = st.session_state.get("enable_chatgpt_api", False)
    
    # Debug: Print checkbox states
    print(f"DEBUG: ChatGPT WebUI enabled: {webui_enabled}, API enabled: {api_enabled}")
    
    if not webui_enabled and not api_enabled:
        print("DEBUG: Neither WebUI nor API enabled, returning early")
        return  # Nothing to start
    
    st.session_state.concurrent_streaming_active = True
    st.session_state.webui_streaming_text = ""
    st.session_state.api_streaming_text = ""
    st.session_state.webui_stream_complete = not webui_enabled  # Mark as complete if not enabled
    st.session_state.api_stream_complete = not api_enabled     # Mark as complete if not enabled
    st.session_state.generating_response = webui_enabled
    st.session_state.generating_api_response = api_enabled
    st.session_state.stop_streaming = False
    
    # Store question for logging when responses complete
    st.session_state.pending_log_question = question.strip()
    
    # Start Web UI streaming thread only if enabled
    if webui_enabled:
        print("DEBUG: Starting WebUI streaming worker")
        start_thread(webui_streaming_worker, question)
    else:
        print("DEBUG: WebUI disabled, not starting WebUI worker")
    
    # Start API streaming thread only if enabled
    if api_enabled:
        print("DEBUG: Starting API streaming worker")
        start_thread(api_streaming_worker, question)
    else:
        print("DEBUG: API disabled, not starting API worker")

def webui_streaming_worker(question):
    """Worker thread for Web UI streaming using direct streaming_chat - updates session state incrementally"""
    try:
        # Double-check that WebUI is enabled before proceeding
        if not st.session_state.get("enable_chatgpt_webui", False):
            st.session_state.webui_stream_complete = True
            st.session_state.generating_response = False
            return
        
        # Store original prompt for logging
        original_prompt = question.strip()
        cleaned_prompt = 'Answer in clean raw markdown language without contentReference. ' +original_prompt + ". Answer in clean raw markdown language without citations or contentReference.  Wrapp the entire response in a markdown code block to show the actual syntax"
        
        # Store the Web UI question for logging
        st.session_state.pending_log_webui_question = cleaned_prompt
        
        # Add to conversation history
        st.session_state.conversation_history.append({"role": "user", "content": cleaned_prompt})
        
        full_response = ""
        previous = ""
        response_started = False
        
        # Create event loop for async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Use the direct streaming function
            async def stream_response():
                nonlocal full_response, previous, response_started
                
                async for chunk in send_message_with_streaming(cleaned_prompt, TIMEOUT_SEC):
                    if st.session_state.stop_streaming:
                        break
                    
                    status = chunk.get("status")
                    content = chunk.get("content", "")
                    
                    if status == "started":
                        response_started = True
                        st.session_state.webui_streaming_text = "🚀 Assistant started typing..."
                    elif status == "streaming":
                        # Update session state with streaming content
                        if len(content) > len(previous):
                            # Smart streaming logic (same as simple_ask_chatgpt.py)
                            safe_patterns = [
                                '\n\n', '\n- ', '\n## ', '\n### ', '. ', '! ', '? ', 
                                ', ', '; ', ': ', '**.', '**,', '**:', '`.', '`,', '```\n'
                            ]
                            
                            last_safe_pos = len(previous)
                            for pattern in safe_patterns:
                                pos = content.rfind(pattern, len(previous))
                                if pos != -1 and pos + len(pattern) > last_safe_pos:
                                    last_safe_pos = pos + len(pattern)
                            
                            space_pos = content.rfind(' ', len(previous))
                            if space_pos != -1 and space_pos + 1 > last_safe_pos:
                                check_pos = space_pos + 1
                                if check_pos < len(content):
                                    before_space = content[max(0, space_pos-5):space_pos]
                                    after_space = content[space_pos:min(len(content), space_pos+5)]
                                    if not ('**' in before_space and '**' not in after_space) and not ('`' in before_space and '`' not in after_space):
                                        last_safe_pos = check_pos
                            
                            if last_safe_pos > len(previous) + 15:
                                new_chunk = content[len(previous):last_safe_pos]
                                full_response += new_chunk
                                # Update session state for UI display
                                st.session_state.webui_streaming_text = full_response + "▌"
                                previous = content[:last_safe_pos]
                            elif len(content) > len(previous) + 150:
                                force_pos = len(previous) + 100
                                last_space = content.rfind(' ', len(previous), force_pos)
                                if last_space > len(previous):
                                    new_chunk = content[len(previous):last_space + 1]
                                    full_response += new_chunk
                                    st.session_state.webui_streaming_text = full_response + "▌"
                                    previous = content[:last_space + 1]
                    elif status == "complete":
                        if len(content) > len(previous):
                            remaining = content[len(previous):]
                            full_response += remaining
                        elif not response_started:
                            full_response = content
                        
                        # Final update to session state
                        st.session_state.webui_streaming_text = full_response
                        break
                    elif status in ["timeout", "error"]:
                        st.session_state.webui_streaming_text = f"Streaming error: {content}"
                        st.session_state.webui_stream_complete = True
                        st.session_state.generating_response = False
                        return
            
            # Run the async streaming
            loop.run_until_complete(stream_response())
            
        finally:
            loop.close()
        
        # Store final response
        if full_response:
            st.session_state.conversation_history.append({"role": "assistant", "content": full_response})
            st.session_state.chatgpt_response = full_response
        
        st.session_state.webui_stream_complete = True
        st.session_state.generating_response = False
        
    except Exception as e:
        st.session_state.webui_streaming_text = f"Error: {str(e)}"
        st.session_state.webui_stream_complete = True
        st.session_state.generating_response = False

def api_streaming_worker(question):
    """Worker thread for API streaming - updates session state incrementally"""
    try:
        # Double-check that API is enabled before proceeding
        if not st.session_state.get("enable_chatgpt_api", False):
            st.session_state.api_stream_complete = True
            st.session_state.generating_api_response = False
            return
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Store the API question for logging
        st.session_state.pending_log_api_question = question
        
        # Add to separate API conversation history
        st.session_state.api_conversation_history.append({"role": "user", "content": question})
        
        # Use separate API conversation history
        messages = st.session_state.api_conversation_history
        
        full_response = ""
        
        # Stream the response
        stream = client.chat.completions.create(
            model=st.session_state.selected_model,
            messages=messages,
            stream=True
        )
        
        st.session_state.api_streaming_text = "🚀 API started typing..."
        
        for chunk in stream:
            if st.session_state.stop_streaming:
                break
                
            if chunk.choices[0].delta.content is not None:
                full_response += chunk.choices[0].delta.content
                # Update session state with cursor
                st.session_state.api_streaming_text = full_response + "▌"
        
        # Final update without cursor
        st.session_state.api_streaming_text = full_response
        st.session_state.api_response = full_response
        
        # Add response to separate API conversation history
        if full_response:
            st.session_state.api_conversation_history.append({"role": "assistant", "content": full_response})
        
        st.session_state.api_stream_complete = True
        st.session_state.generating_api_response = False
        
    except Exception as e:
        st.session_state.api_streaming_text = f"Error: {str(e)}"
        st.session_state.api_stream_complete = True
        st.session_state.generating_api_response = False

def get_chatgpt_response(prompt, show_streaming=True, container=None):
    """Get streaming response from ChatGPT"""
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        st.session_state.conversation_history.append({"role": "user", "content": prompt})
        
        # Where to print?
        if show_streaming:
            if container:
                with container:
                    response_placeholder = st.empty()
            else:
                response_placeholder = st.empty()
        else:
            response_placeholder = None
        full_response = ""
        
        # Reset stop streaming flag
        st.session_state.stop_streaming = False
        
        # Stream the response
        stream = client.chat.completions.create(
            model=st.session_state.selected_model,
            messages=st.session_state.conversation_history,
            stream=True
        )
        
        for chunk in stream:
            # Check if user requested to stop streaming
            if st.session_state.stop_streaming:
                if show_streaming and response_placeholder:
                    # Clean Unicode surrogates before displaying
                    clean_response = full_response.encode('utf-8', errors='replace').decode('utf-8')
                    response_placeholder.markdown(clean_response + "\n\n*[Streaming stopped by user]*")
                break
                
            if chunk.choices[0].delta.content is not None:
                full_response += chunk.choices[0].delta.content
                if show_streaming and response_placeholder:
                    # Clean Unicode surrogates before displaying
                    clean_response = full_response.encode('utf-8', errors='replace').decode('utf-8')
                    response_placeholder.markdown(clean_response + "▌")
        
        # Remove the cursor and show final response (if not stopped)
        if not st.session_state.stop_streaming and show_streaming and response_placeholder:
            # Clean Unicode surrogates before displaying
            clean_response = full_response.encode('utf-8', errors='replace').decode('utf-8')
            response_placeholder.markdown(clean_response)
        
        # Add the complete response to conversation history
        if full_response:
            st.session_state.conversation_history.append({"role": "assistant", "content": full_response})
        
        return full_response
    except Exception as e:
        st.error(f"ChatGPT API error: {str(e)}")
        return None

def render_chatgpt_responses():
    """Render the ChatGPT response UI with tabs containing Web UI and API columns"""
    if not (st.session_state.transcription and not st.session_state.recording):
        return
        
    st.subheader("🤖 ChatGPT Response")

    # Show generating status
    if st.session_state.generating_response or st.session_state.generating_api_response:
        active_streams = []
        if st.session_state.generating_response:
            active_streams.append("Web UI")
        if st.session_state.generating_api_response:
            active_streams.append("API")
        st.info(f"🔄 Generating responses: {', '.join(active_streams)}")

    # Control buttons row
    button_col1, button_col2, button_col3 = st.columns([1, 1, 2])
    
    # Stop button for concurrent streaming
    with button_col1:
        if st.session_state.concurrent_streaming_active:
            if st.button("🛑 Stop All Streaming", key="chatgpt_stop_streaming"):
                st.session_state.stop_streaming = True
                st.session_state.concurrent_streaming_active = False
                st.session_state.generating_response = False
                st.session_state.generating_api_response = False
                st.rerun()
    
    # Session History button
    with button_col2:
        if st.button("📚 Session History", key="chatgpt_history_button"):
            st.session_state.show_chatgpt_history = not st.session_state.get("show_chatgpt_history", False)
            st.rerun()

    # Show session history if toggled
    if st.session_state.get("show_chatgpt_history", False):
        with st.expander("📚 ChatGPT Web UI Session History", expanded=True):
            show_chatgpt_session_history()

    # Determine which columns to show based on enabled checkboxes
    webui_enabled = st.session_state.get("enable_chatgpt_webui", False)
    api_enabled = st.session_state.get("enable_chatgpt_api", False)
    
    if webui_enabled and api_enabled:
        # Show both columns side-by-side
        col_web, col_api = st.columns(2)
        
        # Web UI pane
        with col_web:
            st.markdown('<div class="box-header">🌐 Web UI</div>', unsafe_allow_html=True)
            
            remove='markdown\nCopy\nEdit\n'
            if st.session_state.webui_streaming_text:
                # Show live streaming updates
                with st.container():
                    st.markdown(st.session_state.webui_streaming_text.strip(remove))
            elif st.session_state.chatgpt_response and not st.session_state.concurrent_streaming_active:
                # Show final response when not streaming
                clean = st.session_state.chatgpt_response.encode("utf-8", errors="replace").decode("utf-8")
                with st.container():
                    st.markdown(clean.strip(remove))
            elif st.session_state.generating_response:
                st.info("Response will appear here…")
            else:
                st.info("Click **Get AI Response** to generate responses")

        # API pane
        with col_api:
            st.markdown('<div class="box-header">⚡ API</div>', unsafe_allow_html=True)
            
            if st.session_state.api_streaming_text:
                # Show live streaming updates
                with st.container():
                    st.markdown(st.session_state.api_streaming_text)
            elif st.session_state.api_response and not st.session_state.concurrent_streaming_active:
                # Show final response when not streaming
                with st.container():
                    st.markdown(st.session_state.api_response)
            elif st.session_state.generating_api_response:
                st.info("API response will appear here…")
            else:
                st.info("Responses will appear here")
                
    elif webui_enabled:
        # Show only Web UI column (full width)
        st.markdown('<div class="box-header">🌐 Web UI</div>', unsafe_allow_html=True)
        
        remove='markdown\nCopy\nEdit\n'
        if st.session_state.webui_streaming_text:
            # Show live streaming updates
            with st.container():
                st.markdown(st.session_state.webui_streaming_text.strip(remove))
        elif st.session_state.chatgpt_response and not st.session_state.concurrent_streaming_active:
            # Show final response when not streaming
            clean = st.session_state.chatgpt_response.encode("utf-8", errors="replace").decode("utf-8")
            with st.container():
                st.markdown(clean.strip(remove))
        elif st.session_state.generating_response:
            st.info("Response will appear here…")
        else:
            st.info("Click **Get AI Response** to generate responses")
            
    elif api_enabled:
        # Show only API column (full width)
        st.markdown('<div class="box-header">⚡ API</div>', unsafe_allow_html=True)
        
        if st.session_state.api_streaming_text:
            # Show live streaming updates
            with st.container():
                st.markdown(st.session_state.api_streaming_text)
        elif st.session_state.api_response and not st.session_state.concurrent_streaming_active:
            # Show final response when not streaming
            with st.container():
                st.markdown(st.session_state.api_response)
        elif st.session_state.generating_api_response:
            st.info("API response will appear here…")
        else:
            st.info("Responses will appear here")
    else:
        # Neither enabled
        st.info("Enable WebUI and/or API checkboxes above to see ChatGPT responses")

def handle_concurrent_streaming():
    """Handle auto-refresh and completion logic for concurrent streaming - now handled centrally in main app"""
    # This function is now a no-op since refresh logic is centralized in the main app
    pass

def load_chatgpt_session_history():
    """Load ChatGPT session history from individual log files"""
    try:
        chatgpt_logs_dir = "logs/chatgpt"
        if not os.path.exists(chatgpt_logs_dir):
            return []
        
        history_files = []
        # Get all chat_session_history files
        for filename in os.listdir(chatgpt_logs_dir):
            if filename.startswith("chat_session_history_") and filename.endswith(".json"):
                filepath = os.path.join(chatgpt_logs_dir, filename)
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
        st.error(f"Error loading ChatGPT session history: {str(e)}")
        return []

def show_chatgpt_session_history():
    """Display ChatGPT Web UI session history in a popup-style expander"""
    history = load_chatgpt_session_history()
    
    if not history:
        st.info("No ChatGPT session history found.")
        return
    
    st.subheader("📚 ChatGPT Web UI Session History")
    st.write(f"Found {len(history)} conversation(s)")
    
    for i, entry in enumerate(history):
        timestamp = entry.get("timestamp", "Unknown")
        question = entry.get("question", "No question")
        webui_answer = entry.get("webui_answer", "No Web UI answer")
        model = entry.get("model", "Unknown model")
        
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
            
            st.markdown(f"**🤖 Model:** {model}")
            
            if webui_answer and webui_answer != "No Web UI answer":
                st.markdown("**💬 ChatGPT Web UI Response:**")
                
                # Clean the response text like in the main UI
                def clean_chatgpt_text(text):
                    """Remove common UI artifacts from ChatGPT's response"""
                    if not text:
                        return text
                    
                    # Clean up common UI artifacts
                    remove_artifacts = ['markdown\nCopy\nEdit\n', 'markdown\n', 'Copy\n', 'Edit\n']
                    for artifact in remove_artifacts:
                        text = text.replace(artifact, '')
                    
                    return text.strip()
                
                cleaned_answer = clean_chatgpt_text(webui_answer)
                st.markdown(cleaned_answer)
            else:
                st.info("No Web UI response recorded")
            
            # Show API response if available
            api_answer = entry.get("api_answer")
            if api_answer:
                st.markdown("**⚡ ChatGPT API Response:**")
                st.markdown(api_answer)

def handle_stopped_streaming():
    """Handle stopped streaming cleanup"""
    if st.session_state.stop_streaming and (st.session_state.generating_response or st.session_state.generating_api_response):
        st.session_state.generating_response = False
        st.session_state.generating_api_response = False
        st.session_state.stop_streaming = False
        st.session_state.manual_transcription = None  # Clear manual transcription if stopped
        st.info("🛑 Streaming stopped by user")
