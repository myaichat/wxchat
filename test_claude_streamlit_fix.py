#!/usr/bin/env python3
"""
Standalone test script for claude_streaming_chat_streamlit_fix.py

Usage:
    python test_claude_streamlit_fix.py "Your question here"
    python test_claude_streamlit_fix.py "What is Python?" --port 9222
    python test_claude_streamlit_fix.py "Hello Claude" --no-streaming
"""

import sys
import argparse
import asyncio
from chat_handlers.claude_streaming_chat_streamlit_fix import ask_claude, ask_claude_async

def main():
    """Main function to test the Streamlit-safe Claude streaming chat"""
    parser = argparse.ArgumentParser(
        description='Test Claude Streaming Chat Bot (Streamlit-Safe Version)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_claude_streamlit_fix.py "What is Python?"
  python test_claude_streamlit_fix.py "Explain machine learning" --port 9223
  python test_claude_streamlit_fix.py "Hello" --no-streaming
  
Prerequisites:
  Make sure Chrome is running with debug enabled:
  - Run: start_chrome_debug.ps1
  - Or manually: chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
  - Open Claude.ai in the browser and log in
        """
    )
    
    parser.add_argument(
        'question',
        help='Question to ask Claude'
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=9222,
        help='Chrome debug port (default: 9222)'
    )
    
    parser.add_argument(
        '--no-streaming',
        action='store_true',
        help='Disable streaming mode and get complete response at once'
    )
    
    parser.add_argument(
        '--async-mode',
        action='store_true',
        help='Use async version of the function'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='Claude Streaming Chat Bot Test (Streamlit-Safe) 1.0'
    )
    
    args = parser.parse_args()
    
    if not args.question.strip():
        print("Error: Question cannot be empty")
        sys.exit(1)
    
    print("=" * 60)
    print("🤖 Claude Streaming Chat Bot Test (Streamlit-Safe)")
    print("=" * 60)
    print(f"Question: {args.question}")
    print(f"Debug Port: {args.port}")
    print(f"Streaming: {'No' if args.no_streaming else 'Yes'}")
    print(f"Mode: {'Async' if args.async_mode else 'Sync'}")
    print("=" * 60)
    
    try:
        if args.async_mode:
            # Use async version
            response = asyncio.run(ask_claude_async(
                question=args.question,
                debug_port=args.port,
                streaming=not args.no_streaming
            ))
        else:
            # Use sync version
            response = ask_claude(
                question=args.question,
                debug_port=args.port,
                streaming=not args.no_streaming
            )
        
        print("\n" + "=" * 60)
        print("📝 FINAL RESPONSE:")
        print("=" * 60)
        
        if response:
            print(response)
            print("\n" + "=" * 60)
            print(f"✅ Success! Response length: {len(response)} characters")
        else:
            print("❌ No response received")
            print("\n" + "=" * 60)
            print("❌ Failed to get response from Claude")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error during test: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Chrome is running with debug mode:")
        print("   powershell -ExecutionPolicy Bypass -File start_chrome_debug.ps1")
        print("2. Make sure Claude.ai is open and logged in")
        print("3. Check if the debug port is accessible:")
        print(f"   curl http://localhost:{args.port}/json")
        sys.exit(1)

if __name__ == "__main__":
    main()
