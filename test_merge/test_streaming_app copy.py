import streamlit as st
import asyncio
from streaming_chat import send_message_with_streaming

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "streaming_response" not in st.session_state:
    st.session_state.streaming_response = ""
if "is_streaming" not in st.session_state:
    st.session_state.is_streaming = False

st.title("🚀 Streaming Chat Test")
st.write("Test the streaming chat functionality")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Input form
with st.form("chat_form", clear_on_submit=True):
    question = st.text_input("Enter your question:", placeholder="Ask me anything...")
    submitted = st.form_submit_button("Send", disabled=st.session_state.is_streaming)

# Handle form submission
if submitted and question and not st.session_state.is_streaming:
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": question})
    
    # Set streaming state
    st.session_state.is_streaming = True
    st.session_state.streaming_response = ""
    
    # Display user message
    with st.chat_message("user"):
        st.write(question)
    
    # Create placeholder for streaming response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        
        # Stream the response
        async def stream_response():
            full_response = ""
            try:
                async for response in send_message_with_streaming(question, timeout=60):
                    status = response.get("status", "")
                    content = response.get("content", "")
                    
                    if status == "started":
                        response_placeholder.markdown("🔄 Starting response...")
                    elif status == "streaming":
                        full_response = content
                        response_placeholder.markdown(full_response + "▌")
                    elif status == "complete":
                        full_response = content
                        response_placeholder.markdown(full_response)
                        break
                    elif status in ["timeout", "error"]:
                        error_msg = f"❌ Error: {content}" if content else "❌ Request timed out or failed"
                        response_placeholder.markdown(error_msg)
                        full_response = error_msg
                        break
                        
                return full_response
            except Exception as e:
                error_msg = f"❌ Exception: {str(e)}"
                response_placeholder.markdown(error_msg)
                return error_msg
        
        # Run the async streaming function
        try:
            final_response = asyncio.run(stream_response())
            
            # Add assistant response to chat history
            if final_response:
                st.session_state.messages.append({"role": "assistant", "content": final_response})
                
        except Exception as e:
            error_msg = f"❌ Failed to process request: {str(e)}"
            response_placeholder.markdown(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
        
        finally:
            # Reset streaming state
            st.session_state.is_streaming = False
            st.rerun()

# Show streaming status
if st.session_state.is_streaming:
    st.info("🔄 Streaming response...")

# Clear chat button
if st.button("Clear Chat"):
    st.session_state.messages = []
    st.session_state.streaming_response = ""
    st.session_state.is_streaming = False
    st.rerun()

# Debug info
with st.expander("Debug Info"):
    st.write("**Session State:**")
    st.json({
        "messages_count": len(st.session_state.messages),
        "is_streaming": st.session_state.is_streaming,
        "streaming_response_length": len(st.session_state.streaming_response)
    })
