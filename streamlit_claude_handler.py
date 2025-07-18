"""
Streamlit-compatible Claude handler that replaces Playwright functionality.
This provides the same interface as the original claude_streaming_chat.py
but works within Streamlit applications.
"""

import streamlit as st
import requests
import json
import os
from typing import Optional, Generator, Dict, Any
import time
from datetime import datetime
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

class StreamlitClaudeHandler:
    """
    Streamlit-compatible Claude handler that provides the same functionality
    as the original Playwright-based handler but works in Streamlit.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.base_url = "https://api.anthropic.com/v1"
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        self.start_time = time.time()
    
    def log(self, message: str, operation_name: Optional[str] = None):
        """Log message with timestamp (compatible with original)"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        total_elapsed = time.time() - self.start_time
        
        if operation_name:
            st.write(f"[{timestamp}] (+{total_elapsed:.2f}s) [{operation_name}] {message}")
        else:
            st.write(f"[{timestamp}] (+{total_elapsed:.2f}s) {message}")
    
    def ask_claude_streaming(self, question: str, model: str = "claude-3-sonnet-20240229") -> Generator[str, None, None]:
        """
        Stream Claude's response in real-time for Streamlit.
        
        Args:
            question (str): The question to ask
            model (str): Claude model to use
            
        Yields:
            str: Chunks of Claude's response
        """
        if not self.api_key:
            yield "Error: ANTHROPIC_API_KEY not found. Please set it in your environment variables."
            return
            
        try:
            payload = {
                "model": model,
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": question
                    }
                ],
                "stream": True
            }
            
            response = requests.post(
                f"{self.base_url}/messages",
                headers=self.headers,
                json=payload,
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data_str = line[6:]  # Remove 'data: ' prefix
                            if data_str.strip() == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                if data.get('type') == 'content_block_delta':
                                    text = data.get('delta', {}).get('text', '')
                                    if text:
                                        yield text
                            except json.JSONDecodeError:
                                continue
            else:
                yield f"API Error: {response.status_code} - {response.text}"
                
        except Exception as e:
            yield f"Error calling Claude API: {e}"
    
    def ask_claude(self, question: str, model: str = "claude-3-sonnet-20240229") -> Optional[str]:
        """
        Send a question to Claude and get complete response.
        
        Args:
            question (str): The question to ask
            model (str): Claude model to use
            
        Returns:
            str: Claude's complete response or None if failed
        """
        full_response = ""
        for chunk in self.ask_claude_streaming(question, model):
            if not chunk.startswith("Error:"):
                full_response += chunk
            else:
                return None
        
        return full_response if full_response else None


def create_streamlit_claude_app():
    """
    Create a complete Streamlit app that replaces the Playwright functionality.
    """
    st.title("Claude Chat - Streamlit Compatible")
    st.write("This app provides the same functionality as the Playwright-based Claude chat but works in Streamlit.")
    
    # Initialize the handler
    if 'claude_handler' not in st.session_state:
        st.session_state.claude_handler = StreamlitClaudeHandler()
    
    # API Key input
    api_key = st.text_input("Anthropic API Key (optional if set in environment)", type="password")
    if api_key:
        st.session_state.claude_handler.api_key = api_key
        st.session_state.claude_handler.headers["x-api-key"] = api_key
    
    # Question input
    question = st.text_input("Ask Claude a question:", value="how ry?")
    
    # Model selection
    model = st.selectbox(
        "Select Claude model:",
        ["claude-3-sonnet-20240229", "claude-3-haiku-20240307", "claude-3-opus-20240229"]
    )
    
    # Streaming toggle
    use_streaming = st.checkbox("Use streaming response", value=True)
    
    if st.button("Send Question"):
        if question:
            handler = st.session_state.claude_handler
            
            if use_streaming:
                st.write("**Streaming Response:**")
                response_container = st.empty()
                full_response = ""
                
                for chunk in handler.ask_claude_streaming(question, model):
                    if not chunk.startswith("Error:"):
                        full_response += chunk
                        response_container.write(full_response)
                    else:
                        st.error(chunk)
                        break
            else:
                st.write("**Complete Response:**")
                with st.spinner("Getting response from Claude..."):
                    response = handler.ask_claude(question, model)
                    if response:
                        st.write(response)
                    else:
                        st.error("Failed to get response from Claude")
        else:
            st.warning("Please enter a question")


# Drop-in replacement functions that match the original API
def ask_claude(question: str, debug_port: int = 9222, streaming: bool = True) -> Optional[str]:
    """
    Drop-in replacement for the original ask_claude function.
    
    Args:
        question (str): The question to ask Claude
        debug_port (int): Ignored (for compatibility)
        streaming (bool): Whether to use streaming mode
    
    Returns:
        str: Claude's response, or None if failed
    """
    handler = StreamlitClaudeHandler()
    
    if streaming:
        full_response = ""
        for chunk in handler.ask_claude_streaming(question):
            if not chunk.startswith("Error:"):
                full_response += chunk
            else:
                return None
        return full_response if full_response else None
    else:
        return handler.ask_claude(question)


async def ask_claude_async(question: str, debug_port: int = 9222, streaming: bool = True) -> Optional[str]:
    """
    Async version for compatibility with original API.
    
    Args:
        question (str): The question to ask Claude
        debug_port (int): Ignored (for compatibility)
        streaming (bool): Whether to use streaming mode
    
    Returns:
        str: Claude's response, or None if failed
    """
    # Run the synchronous version in a thread pool
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        return await loop.run_in_executor(executor, ask_claude, question, debug_port, streaming)


def main_async(question: Optional[str] = None, debug_port: int = 9222, streaming: bool = True) -> Optional[str]:
    """
    Drop-in replacement for the original main_async function.
    
    Args:
        question (str): The question to ask Claude
        debug_port (int): Ignored (for compatibility)
        streaming (bool): Whether to use streaming mode
    
    Returns:
        str: Claude's response, or None if failed
    """
    if not question:
        question = "How are you?"
    
    return ask_claude(question, debug_port, streaming)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Command line usage - same as original
        question = sys.argv[1]
        print(f"Question: {question}")
        
        handler = StreamlitClaudeHandler()
        
        print("\n=== STREAMING RESPONSE ===")
        full_response = ""
        
        for chunk in handler.ask_claude_streaming(question):
            if not chunk.startswith("Error:"):
                print(chunk, end='', flush=True)
                full_response += chunk
            else:
                print(f"\nError: {chunk}")
                break
        
        print("\n=== END OF STREAMING ===")
        
        if full_response:
            print(f"Complete response received ({len(full_response)} characters)")
        else:
            print("No response received")
    else:
        # Run Streamlit app
        create_streamlit_claude_app()
