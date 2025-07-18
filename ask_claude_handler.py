#!/usr/bin/env python3
"""
Test script for claude_handler.py - accepts question as argument and tests the handler functionality
"""

import sys
import argparse
import asyncio
import threading
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=Path(".") / ".env", override=True)

# Mock Streamlit session state for testing
class MockSessionState:
    def __init__(self):
        self.data = {}
        
    def __getattr__(self, name):
        return self.data.get(name, None)
        
    def __setattr__(self, name, value):
        if name == 'data':
            super().__setattr__(name, value)
        else:
            self.data[name] = value
            
    def get(self, name, default=None):
        return self.data.get(name, default)

# Mock Streamlit runtime module
class MockScriptRunner:
    def add_script_run_ctx(self, thread):
        pass  # No-op for testing

class MockRuntime:
    def __init__(self):
        self.scriptrunner = MockScriptRunner()

# Mock Streamlit module
class MockStreamlit:
    def __init__(self):
        self.session_state = MockSessionState()
        self.runtime = MockRuntime()
        
    def error(self, message):
        print(f"ERROR: {message}")
        
    def info(self, message):
        print(f"INFO: {message}")
        
    def success(self, message):
        print(f"SUCCESS: {message}")
        
    def rerun(self):
        pass  # No-op for testing

# Replace streamlit with mock
mock_st = MockStreamlit()
sys.modules['streamlit'] = mock_st
sys.modules['streamlit.runtime'] = mock_st.runtime
sys.modules['streamlit.runtime.scriptrunner'] = mock_st.runtime.scriptrunner
import streamlit as st

# Initialize mock session state
st.session_state.selected_model = "claude-3-5-sonnet-20241022"
st.session_state.claude_conversation_history = []
st.session_state.claude_api_conversation_history = []
st.session_state.claude_response = None
st.session_state.claude_api_response = None
st.session_state.claude_webui_streaming_text = ""
st.session_state.claude_api_streaming_text = ""
st.session_state.claude_webui_stream_complete = False
st.session_state.claude_api_stream_complete = False
st.session_state.claude_concurrent_streaming_active = False
st.session_state.claude_generating_response = False
st.session_state.claude_generating_api_response = False
st.session_state.stop_streaming = False
st.session_state.claude_pending_log_question = None
st.session_state.claude_pending_log_webui_question = None
st.session_state.claude_pending_log_api_question = None
st.session_state.session_log_file = "test_claude_session.json"

# Now import the claude_handler
try:
    from chat_handlers import claude_handler
    print("✅ Successfully imported claude_handler")
except Exception as e:
    print(f"❌ Failed to import claude_handler: {e}")
    sys.exit(1)

def test_api_only(question):
    """Test Claude API functionality only"""
    print(f"\n🧪 Testing Claude API with question: '{question}'")
    print("=" * 60)
    
    # Set up for API-only test
    st.session_state.claude_concurrent_streaming_active = True
    st.session_state.claude_api_streaming_text = ""
    st.session_state.claude_api_stream_complete = False
    st.session_state.claude_generating_api_response = True
    st.session_state.stop_streaming = False
    
    # Start API streaming in a thread
    api_thread = threading.Thread(
        target=claude_handler.api_streaming_worker, 
        args=(question,), 
        daemon=True
    )
    api_thread.start()
    
    # Monitor progress
    print("🚀 Starting Claude API streaming...")
    last_text = ""
    
    while st.session_state.claude_generating_api_response:
        current_text = st.session_state.claude_api_streaming_text
        if current_text != last_text:
            # Show only new content
            if len(current_text) > len(last_text):
                new_content = current_text[len(last_text):]
                print(new_content, end='', flush=True)
            last_text = current_text
        time.sleep(0.1)
    
    # Wait for thread to complete
    api_thread.join(timeout=30)
    
    print(f"\n\n✅ API Response completed!")
    print(f"📝 Final response length: {len(st.session_state.claude_api_response or '')}")
    
    if st.session_state.claude_api_response:
        print("\n" + "="*60)
        print("FINAL API RESPONSE:")
        print("="*60)
        print(st.session_state.claude_api_response)
        print("="*60)
    
    return st.session_state.claude_api_response

def test_webui_only(question):
    """Test Claude Web UI functionality only"""
    print(f"\n🧪 Testing Claude Web UI with question: '{question}'")
    print("=" * 60)
    
    # Set up for Web UI-only test
    st.session_state.claude_concurrent_streaming_active = True
    st.session_state.claude_webui_streaming_text = ""
    st.session_state.claude_webui_stream_complete = False
    st.session_state.claude_generating_response = True
    st.session_state.stop_streaming = False
    
    # Start Web UI streaming in a thread
    webui_thread = threading.Thread(
        target=claude_handler.webui_streaming_worker, 
        args=(question,), 
        daemon=True
    )
    webui_thread.start()
    
    # Monitor progress
    print("🚀 Starting Claude Web UI streaming...")
    last_text = ""
    
    while st.session_state.claude_generating_response:
        current_text = st.session_state.claude_webui_streaming_text
        if current_text != last_text:
            print(f"📱 Web UI Status: {current_text[:100]}{'...' if len(current_text) > 100 else ''}")
            last_text = current_text
        time.sleep(0.5)
    
    # Wait for thread to complete
    webui_thread.join(timeout=60)
    
    print(f"\n✅ Web UI Response completed!")
    print(f"📝 Final response length: {len(st.session_state.claude_response or '')}")
    
    if st.session_state.claude_response:
        print("\n" + "="*60)
        print("FINAL WEB UI RESPONSE:")
        print("="*60)
        print(st.session_state.claude_response)
        print("="*60)
    elif st.session_state.claude_webui_streaming_text:
        print("\n" + "="*60)
        print("WEB UI STATUS/ERROR:")
        print("="*60)
        print(st.session_state.claude_webui_streaming_text)
        print("="*60)
    
    return st.session_state.claude_response

def test_concurrent(question):
    """Test both Claude API and Web UI concurrently"""
    print(f"\n🧪 Testing Claude Concurrent Streaming with question: '{question}'")
    print("=" * 60)
    
    # Use the handler's concurrent streaming function
    claude_handler.start_concurrent_streaming(question)
    
    print("🚀 Starting concurrent streaming (API + Web UI)...")
    
    # Monitor both streams
    while st.session_state.claude_concurrent_streaming_active:
        api_status = "✅ Complete" if st.session_state.claude_api_stream_complete else "🔄 Streaming"
        webui_status = "✅ Complete" if st.session_state.claude_webui_stream_complete else "🔄 Streaming"
        
        print(f"\r📊 API: {api_status} | Web UI: {webui_status}", end='', flush=True)
        time.sleep(0.5)
        
        # Break if both are complete
        if (st.session_state.claude_api_stream_complete and 
            st.session_state.claude_webui_stream_complete):
            break
    
    print(f"\n\n✅ Concurrent streaming completed!")
    
    # Show results
    if st.session_state.claude_api_response:
        print(f"\n📝 API Response length: {len(st.session_state.claude_api_response)}")
        print("="*30 + " API RESPONSE " + "="*30)
        print(st.session_state.claude_api_response[:500] + "..." if len(st.session_state.claude_api_response) > 500 else st.session_state.claude_api_response)
    
    if st.session_state.claude_response:
        print(f"\n📝 Web UI Response length: {len(st.session_state.claude_response)}")
        print("="*30 + " WEB UI RESPONSE " + "="*30)
        print(st.session_state.claude_response[:500] + "..." if len(st.session_state.claude_response) > 500 else st.session_state.claude_response)
    elif st.session_state.claude_webui_streaming_text:
        print(f"\n📱 Web UI Status: {st.session_state.claude_webui_streaming_text}")

def main():
    parser = argparse.ArgumentParser(
        description='Test Claude Handler - Test the refactored claude_handler.py functionality',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ask_claude_handler.py "What is Python?"
  python ask_claude_handler.py "Explain machine learning" --mode api
  python ask_claude_handler.py "Hello Claude" --mode webui
  python ask_claude_handler.py "Write a simple Java program" --mode concurrent
        """
    )
    
    parser.add_argument(
        'question',
        help='Question to ask Claude'
    )
    
    parser.add_argument(
        '--mode', '-m',
        choices=['api', 'webui', 'concurrent'],
        default='api',
        help='Test mode: api (API only), webui (Web UI only), or concurrent (both)'
    )
    
    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=60,
        help='Timeout in seconds (default: 60)'
    )
    
    args = parser.parse_args()
    
    print("🎯 Claude Handler Test Script")
    print("=" * 60)
    print(f"Question: {args.question}")
    print(f"Mode: {args.mode}")
    print(f"Timeout: {args.timeout}s")
    
    try:
        if args.mode == 'api':
            result = test_api_only(args.question)
        elif args.mode == 'webui':
            result = test_webui_only(args.question)
        elif args.mode == 'concurrent':
            test_concurrent(args.question)
            result = st.session_state.claude_api_response or st.session_state.claude_response
        
        if result:
            print(f"\n🎉 Test completed successfully!")
            print(f"📊 Response received: {len(result)} characters")
        else:
            print(f"\n⚠️  Test completed but no response received")
            print("This might be expected for Web UI mode if Chrome debug is not set up")
            
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Test interrupted by user")
        st.session_state.stop_streaming = True
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
