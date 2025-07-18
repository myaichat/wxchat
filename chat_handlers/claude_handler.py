"""
Claude Handler Module - Handles both Web UI and API streaming responses
"""
import streamlit as st
import asyncio
import threading
import datetime
import json
import os
import anthropic
from streamlit.runtime.scriptrunner import add_script_run_ctx
# Lazy import to avoid startup issues
StreamingClaude = None

TIMEOUT_SEC = 60

def start_thread(fn, *args, **kwargs):
    """Utility – start a daemon thread that can call Streamlit commands."""
    th = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    add_script_run_ctx(th)          # <- critical line
    th.start()
    return th

def log_qa_pair(question: str, webui_answer: str = None, api_answer: str = None, webui_question: str = None, api_question: str = None):
    """Log question/answer pair to session log file with both Web UI and API responses and raw questions"""
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
        
        # Append to log file with pretty formatting (each field on new line)
        with open(st.session_state.session_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False, indent=2) + "\n")
            
    except Exception as e:
        st.error(f"Failed to log Q&A pair: {str(e)}")

def start_concurrent_streaming(question):
    """Start both Web UI and API streaming concurrently"""
    st.session_state.claude_concurrent_streaming_active = True
    st.session_state.claude_webui_streaming_text = ""
    st.session_state.claude_api_streaming_text = ""
    st.session_state.claude_webui_stream_complete = False
    st.session_state.claude_api_stream_complete = False
    st.session_state.claude_generating_response = True
    st.session_state.claude_generating_api_response = True
    st.session_state.stop_streaming = False
    
    # Store question for logging when both responses complete
    st.session_state.claude_pending_log_question = question.strip()
    
    # Start Web UI streaming thread (now using direct streaming_chat)
    start_thread(webui_streaming_worker, question)
    
    # Start API streaming thread  
    start_thread(api_streaming_worker, question)

def webui_streaming_worker(question):
    """Worker thread for Web UI streaming using ChromeDebugChatBot - updates session state incrementally"""
    bot = None
    try:
        # Check if we're in a Streamlit environment that might have subprocess issues
        import sys
        import platform
        
        # Early detection of potential Playwright issues
        if platform.system() == "Windows" and hasattr(sys, 'ps1') == False:
            # We're likely in a non-interactive environment on Windows
            st.session_state.claude_webui_streaming_text = "⚠️ Web UI mode may not work in this environment. Using API-only mode is recommended."
        
        # Lazy import StreamingClaude only when needed
        global StreamingClaude
        if StreamingClaude is None:
            try:
                from chat_handlers.claude_streaming_chat import StreamingClaude
            except Exception as import_error:
                st.session_state.claude_webui_streaming_text = f"❌ Import error: Could not import StreamingClaude - {str(import_error)}"
                st.session_state.claude_webui_stream_complete = True
                st.session_state.claude_generating_response = False
                return
        
        # Store original prompt for logging
        original_prompt = question.strip()
        cleaned_prompt = 'Answer in clean raw markdown language. ' +original_prompt + ".  Wrapp the entire response in a markdown code block to show the actual syntax"
        
        # Store the Web UI question for logging
        st.session_state.claude_pending_log_webui_question = cleaned_prompt
        
        # Add to conversation history
        st.session_state.claude_conversation_history.append({"role": "user", "content": cleaned_prompt})
        
        full_response = ""
        
        # Try to create event loop, but handle subprocess issues gracefully
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        except Exception as loop_creation_error:
            error_msg = str(loop_creation_error)
            if "NotImplementedError" in error_msg:
                st.session_state.claude_webui_streaming_text = "❌ Cannot create async event loop in this environment. Web UI mode is not supported. Please use API-only mode."
            else:
                st.session_state.claude_webui_streaming_text = f"❌ Event loop creation failed: {error_msg}"
            st.session_state.claude_webui_stream_complete = True
            st.session_state.claude_generating_response = False
            return
        
        try:
            # Use the ChromeDebugChatBot class properly
            async def stream_response():
                nonlocal full_response, bot
                
                try:
                    st.session_state.claude_webui_streaming_text = "🔄 Connecting to Claude browser tab..."
                    
                    # Create bot instance only when needed
                    bot = StreamingClaude(debug_port=9222)
                    
                    # Connect to existing Chrome tab
                    if bot.get_claude_tab():
                        st.session_state.claude_webui_streaming_text = "🚀 Connected to Claude, starting response..."
                        
                        # Send message and get response
                        result = bot.inject_and_ask(cleaned_prompt)
                        if "Error:" in result or "error" in result.lower():
                            st.session_state.claude_webui_streaming_text = f"❌ {result}"
                            st.session_state.claude_webui_stream_complete = True
                            st.session_state.claude_generating_response = False
                            return
                        
                        # Use custom streaming that updates session state in real-time
                        try:
                            # Wait a moment for the message to be processed
                            import time
                            time.sleep(2)
                            
                            # Custom streaming implementation that updates session state
                            start_time = time.time()
                            last_text = ""
                            last_length = 0
                            no_change_count = 0
                            max_wait = 60
                            update_interval = 0.5
                            
                            while time.time() - start_time < max_wait:
                                if st.session_state.stop_streaming:
                                    break
                                    
                                try:
                                    response_data = bot.get_current_response()
                                    current_text = response_data.get('text', '')
                                    is_generating = response_data.get('generating', False)
                                    current_length = response_data.get('length', 0)
                                    
                                    # Check if we have new content
                                    if current_text != last_text and current_length > 0:
                                        # Update session state with streaming content and cursor
                                        if is_generating:
                                            st.session_state.claude_webui_streaming_text = current_text + "▌"
                                        else:
                                            st.session_state.claude_webui_streaming_text = current_text
                                        
                                        full_response = current_text
                                        last_text = current_text
                                        last_length = current_length
                                        no_change_count = 0
                                    
                                    # Check if response is complete
                                    if current_length > 20 and not is_generating:
                                        full_response = current_text
                                        st.session_state.claude_webui_streaming_text = current_text
                                        break
                                    
                                    # Check for no changes (might indicate completion or error)
                                    if current_text == last_text:
                                        no_change_count += 1
                                        if no_change_count > 10 and current_length > 10:  # 5 seconds of no change
                                            full_response = current_text
                                            st.session_state.claude_webui_streaming_text = current_text
                                            break
                                    
                                    time.sleep(update_interval)
                                    
                                except Exception as e:
                                    st.session_state.claude_webui_streaming_text = f"❌ Error during streaming: {str(e)}"
                                    st.session_state.claude_webui_stream_complete = True
                                    st.session_state.claude_generating_response = False
                                    return
                            
                            # Handle timeout
                            if time.time() - start_time >= max_wait:
                                if last_text:
                                    full_response = last_text
                                    st.session_state.claude_webui_streaming_text = last_text + "\n\n⏰ *Streaming timeout reached*"
                                else:
                                    st.session_state.claude_webui_streaming_text = "❌ Timeout: No response received"
                                    st.session_state.claude_webui_stream_complete = True
                                    st.session_state.claude_generating_response = False
                                    return
                                
                        except Exception as streaming_error:
                            st.session_state.claude_webui_streaming_text = f"❌ Streaming error: {str(streaming_error)}"
                            st.session_state.claude_webui_stream_complete = True
                            st.session_state.claude_generating_response = False
                            return
                        
                        # Final update to session state without cursor
                        st.session_state.claude_webui_streaming_text = full_response
                        
                    else:
                        st.session_state.claude_webui_streaming_text = "❌ Could not connect to Claude browser tab. Make sure Chrome is running with debug enabled and Claude.ai is open."
                        st.session_state.claude_webui_stream_complete = True
                        st.session_state.claude_generating_response = False
                        return
                        
                except Exception as connection_error:
                    # Handle connection-specific errors more gracefully
                    error_msg = str(connection_error)
                    if "NotImplementedError" in error_msg or "subprocess" in error_msg:
                        st.session_state.claude_webui_streaming_text = "❌ Subprocess creation failed. Web UI mode is not supported in this environment. Please use API-only mode or run Chrome with debug mode manually."
                    elif "playwright" in error_msg.lower():
                        st.session_state.claude_webui_streaming_text = "❌ Playwright connection failed. Chrome debug mode may not be available in this environment."
                    else:
                        st.session_state.claude_webui_streaming_text = f"❌ Connection error: {error_msg}"
                    st.session_state.claude_webui_stream_complete = True
                    st.session_state.claude_generating_response = False
                    return
                        
                finally:
                    # Clean up bot resources - StreamingClaude doesn't need explicit cleanup
                    pass
            
            # Run the async streaming with better error handling
            try:
                loop.run_until_complete(stream_response())
            except RuntimeError as runtime_error:
                error_msg = str(runtime_error)
                if "NotImplementedError" in error_msg or "subprocess" in error_msg:
                    st.session_state.claude_webui_streaming_text = "❌ Runtime error: Web UI mode is not supported in this environment. Please disable Web UI and use API-only mode."
                else:
                    st.session_state.claude_webui_streaming_text = f"❌ Runtime error: {error_msg}"
                st.session_state.claude_webui_stream_complete = True
                st.session_state.claude_generating_response = False
            
        except Exception as loop_error:
            # Handle any loop-level errors
            error_msg = str(loop_error)
            if "NotImplementedError" in error_msg or "subprocess" in error_msg:
                st.session_state.claude_webui_streaming_text = "❌ Web UI mode is not supported in this environment. Please disable Claude Web UI checkbox and use API-only mode."
            else:
                st.session_state.claude_webui_streaming_text = f"❌ Loop error: {error_msg}"
            st.session_state.claude_webui_stream_complete = True
            st.session_state.claude_generating_response = False
        finally:
            try:
                loop.close()
            except:
                pass  # Ignore loop cleanup errors
        
        # Store final response
        if full_response:
            st.session_state.claude_conversation_history.append({"role": "assistant", "content": full_response})
            st.session_state.claude_response = full_response
        
        st.session_state.claude_webui_stream_complete = True
        st.session_state.claude_generating_response = False
        
    except Exception as e:
        # Top-level error handling with more specific messages
        error_msg = str(e)
        if "NotImplementedError" in error_msg or "subprocess" in error_msg:
            st.session_state.claude_webui_streaming_text = "❌ Web UI mode is not supported in this environment. Please disable the Claude Web UI checkbox and use API-only mode instead."
        elif "playwright" in error_msg.lower():
            st.session_state.claude_webui_streaming_text = "❌ Playwright is not available in this environment. Please disable Web UI mode and use API-only."
        else:
            st.session_state.claude_webui_streaming_text = f"❌ Error: {error_msg}"
        st.session_state.claude_webui_stream_complete = True
        st.session_state.claude_generating_response = False
    finally:
        # Final cleanup attempt - StreamingClaude doesn't need explicit cleanup
        pass

def api_streaming_worker(question):
    """Worker thread for Claude API streaming - updates session state incrementally"""
    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        # Store the API question for logging
        st.session_state.claude_pending_log_api_question = question
        
        # Add to separate API conversation history
        st.session_state.claude_api_conversation_history.append({"role": "user", "content": question})
        
        # Use separate API conversation history - convert to Claude format
        messages = []
        for msg in st.session_state.claude_api_conversation_history:
            if msg["role"] in ["user", "assistant"]:
                messages.append(msg)
        
        full_response = ""
        
        # Stream the response using Claude API
        with client.messages.stream(
            model="claude-3-5-sonnet-20241022",  # Use Claude model
            max_tokens=4000,
            messages=messages
        ) as stream:
            st.session_state.claude_api_streaming_text = "🚀 Claude API started typing..."
            
            for text in stream.text_stream:
                if st.session_state.stop_streaming:
                    break
                    
                full_response += text
                # Update session state with cursor
                st.session_state.claude_api_streaming_text = full_response + "▌"
        
        # Final update without cursor
        st.session_state.claude_api_streaming_text = full_response
        st.session_state.claude_api_response = full_response
        
        # Add response to separate API conversation history
        if full_response:
            st.session_state.claude_api_conversation_history.append({"role": "assistant", "content": full_response})
        
        st.session_state.claude_api_stream_complete = True
        st.session_state.claude_generating_api_response = False
        
    except Exception as e:
        st.session_state.claude_api_streaming_text = f"Error: {str(e)}"
        st.session_state.claude_api_stream_complete = True
        st.session_state.claude_generating_api_response = False

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

def render_claude_responses():
    """Render the Claude response UI with tabs containing Web UI and API columns"""
    if not (st.session_state.transcription and not st.session_state.recording):
        return
        
    st.subheader("🤖 Claude Response")

    # Show generating status
    if st.session_state.claude_generating_response or st.session_state.claude_generating_api_response:
        active_streams = []
        if st.session_state.claude_generating_response:
            active_streams.append("Web UI")
        if st.session_state.claude_generating_api_response:
            active_streams.append("API")
        st.info(f"🔄 Generating responses: {', '.join(active_streams)}")

    # Stop button for concurrent streaming - placed above tabs
    if st.session_state.claude_concurrent_streaming_active:
        if st.button("🛑 Stop All Streaming", key="claude_stop_streaming"):
            st.session_state.stop_streaming = True
            st.session_state.claude_concurrent_streaming_active = False
            st.session_state.claude_generating_response = False
            st.session_state.claude_generating_api_response = False
            st.rerun()

    # Create tabs for Claude responses
    claude_tab = st.tabs(["🤖 Claude"])
    
    with claude_tab[0]:
        # Two side-by-side panes with concurrent streaming
        col_web, col_api = st.columns(2)

        # Web UI pane
        with col_web:
            st.markdown('<div class="box-header">🌐 Web UI</div>', unsafe_allow_html=True)
            
            def clean_reasoning_text(text):
                """Remove reasoning artifacts from Claude's response"""
                if not text:
                    return text
                
                import re
                
                # Remove common reasoning patterns - but be more careful with markdown
                patterns = [
                    r'^.*?Let me organize this into a comprehensive response\.?\s*',
                    r'^.*?Let me format[^.]*\.\s*',
                    r'^.*?Let me provide[^.]*\.\s*',
                    r'^.*?I\'ll search[^.]*\.\s*',
                    r'^.*?I need to search[^.]*\.\s*',
                    r'^.*?Let me search[^.]*\.\s*',
                    r'^.*?Searching the web[^\n]*\n?',
                    r'^.*?Searching[^\n]*\n?',
                    r'^.*?Thinking\.\.\.\s*\d*s?\s*',
                    r'^.*?Thinking about[^.]*\.\s*',
                    r'^.*?Great! I now have[^.]*\.\s*',
                    r'^.*?Great![^.]*\.\s*',
                    r'^.*?\d+s[^.]*\.\s*',
                    r'^.*?I should[^.]*\.\s*',
                    r'^.*?comprehensive overview\.\s*',
                    r'^.*?Synthesized[^.]*\.\s*',
                    r'^.*?wrapping the entire response in a markdown code block[^.]*\.?\s*',
                    r'^.*?markdown code block to show[^.]*\.?\s*',
                    r'^.*?as requested[^.]*\.?\s*',
                    r'^.*?markdown\s*',
                ]
                
                # Apply all patterns
                for pattern in patterns:
                    text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)
                
                # More precise removal of artifacts before markdown headers - preserve markdown formatting
                # Only remove text that looks like reasoning, not markdown syntax
                text = re.sub(r'^[^#*\n]*?(?=# |## |### )', '', text, flags=re.MULTILINE | re.DOTALL)
                
                # Clean up common UI artifacts
                remove_artifacts = ['markdown\nCopy\nEdit\n', 'markdown\n', 'Copy\n', 'Edit\n']
                for artifact in remove_artifacts:
                    text = text.replace(artifact, '')
                
                return text.strip()
            
            if st.session_state.claude_webui_streaming_text:
                # Show live streaming updates with reasoning removed
                cleaned_text = clean_reasoning_text(st.session_state.claude_webui_streaming_text)
                st.markdown(cleaned_text)
            elif st.session_state.claude_response and not st.session_state.claude_concurrent_streaming_active:
                # Show final response when not streaming with reasoning removed
                cleaned_text = clean_reasoning_text(st.session_state.claude_response)
                st.markdown(cleaned_text)
            elif st.session_state.claude_generating_response:
                st.info("Response will appear here…")
            else:
                st.info("Click **Get Both Responses** to generate responses")

        # API pane
        with col_api:
            st.markdown('<div class="box-header">⚡ API</div>', unsafe_allow_html=True)
            
            if st.session_state.claude_api_streaming_text:
                # Show live streaming updates
                st.markdown(st.session_state.claude_api_streaming_text)
            elif st.session_state.claude_api_response and not st.session_state.claude_concurrent_streaming_active:
                # Show final response when not streaming
                st.markdown(st.session_state.claude_api_response)
            elif st.session_state.claude_generating_api_response:
                st.info("API response will appear here…")
            else:
                st.info("Responses will appear here")

def handle_concurrent_streaming():
    """Handle auto-refresh and completion logic for concurrent streaming"""
    if not st.session_state.claude_concurrent_streaming_active:
        return
        
    # Check if both streams are complete
    if st.session_state.claude_webui_stream_complete and st.session_state.claude_api_stream_complete:
        st.session_state.claude_concurrent_streaming_active = False
        
        # Log both responses when both streams are complete
        if st.session_state.claude_pending_log_question:
            log_qa_pair(
                st.session_state.claude_pending_log_question,
                webui_answer=st.session_state.claude_response,
                api_answer=st.session_state.claude_api_response,
                webui_question=st.session_state.claude_pending_log_webui_question,
                api_question=st.session_state.claude_pending_log_api_question
            )
            # Clear after logging
            st.session_state.claude_pending_log_question = None
            st.session_state.claude_pending_log_webui_question = None
            st.session_state.claude_pending_log_api_question = None
        
        st.success("✅ Both Claude responses completed!")
        st.rerun()
    else:
        # Only auto-refresh if we're actually streaming (not just at startup)
        if (st.session_state.claude_generating_response or 
            st.session_state.claude_generating_api_response):
            import time
            time.sleep(0.2)  # Refresh every 200ms for smoother streaming
            st.rerun()

def handle_stopped_streaming():
    """Handle stopped streaming cleanup"""
    if st.session_state.stop_streaming and (st.session_state.claude_generating_response or st.session_state.claude_generating_api_response):
        st.session_state.claude_generating_response = False
        st.session_state.claude_generating_api_response = False
        st.session_state.stop_streaming = False
        st.session_state.manual_transcription = None  # Clear manual transcription if stopped
        st.info("🛑 Claude streaming stopped by user")

def main():
    """Main function for standalone execution"""
    import sys
    from datetime import datetime
    
    if len(sys.argv) < 2:
        print("Usage: python claude_handler.py 'your question'")
        print("Example: python claude_handler.py 'how are you?'")
        return
    
    question = sys.argv[1]
    
    print("🚀 Claude Handler (Standalone Mode)")
    print("=" * 50)
    print(f"📝 Question: {question}")
    print(f"⏰ Started at: {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    # Import StreamingClaude directly
    try:
        from chat_handlers.claude_streaming_chat import StreamingClaude
    except ImportError:
        try:
            # Try relative import if we're running from within chat_handlers
            from claude_streaming_chat import StreamingClaude
        except ImportError:
            print("❌ Could not import StreamingClaude from claude_streaming_chat")
            print("Make sure you're running from the project root directory")
            return
    
    # Initialize Claude
    claude = StreamingClaude()
    
    # Find Claude tab
    if not claude.get_claude_tab():
        print("❌ No Claude.ai tab found")
        print("Please open https://claude.ai in Chrome and login")
        return
    
    print("✅ Found Claude.ai tab")
    
    # Send question
    print("📤 Sending question...")
    result = claude.inject_and_ask(question)
    print(f"📋 Send result: {result}")
    
    if "Error:" in result or "error" in result.lower():
        print(f"❌ {result}")
        return
    
    # Wait a moment for the message to be processed
    print("⏳ Waiting for Claude to start responding...")
    import time
    time.sleep(2)
    
    # Stream the response
    response = claude.stream_response()
    
    print()
    print("📊 Final Response:")
    print("-" * 50)
    print(response)
    print("-" * 50)
    print(f"📏 Length: {len(response)} characters")
    print(f"⏰ Completed at: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()
