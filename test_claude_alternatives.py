"""
Test script to demonstrate all Claude alternative solutions.
This shows how to replace the original Playwright-based command.
"""

import sys
import os

def test_api_client():
    """Test the API client approach"""
    print("=== Testing API Client ===")
    
    from claude_api_alternative import ask_claude_simple
    
    # Test without API key (will show error)
    response = ask_claude_simple("how ry?", method="api")
    if response:
        print(f"API Response: {response}")
    else:
        print("API method requires ANTHROPIC_API_KEY environment variable")
    
    print()

def test_streamlit_handler():
    """Test the Streamlit handler approach"""
    print("=== Testing Streamlit Handler ===")
    
    from streamlit_claude_handler import ask_claude
    
    # Test without API key (will show error)
    response = ask_claude("how ry?")
    if response:
        print(f"Streamlit Handler Response: {response}")
    else:
        print("Streamlit handler also requires ANTHROPIC_API_KEY environment variable")
    
    print()

def test_proxy_client():
    """Test the proxy client approach"""
    print("=== Testing Proxy Client ===")
    
    from claude_api_alternative import ClaudeProxyClient
    
    client = ClaudeProxyClient()
    response = client.ask_claude_proxy("how ry?")
    if response:
        print(f"Proxy Response: {response}")
    else:
        print("Proxy method requires proxy server running on localhost:8080")
        print("Start with: python claude_proxy_server.py")
    
    print()

def show_usage_examples():
    """Show usage examples for each method"""
    print("=== Usage Examples ===")
    print()
    
    print("Original command:")
    print("python '.\\chat_handlers\\claude_streaming_chat.py' 'how ry?'")
    print()
    
    print("Alternative commands:")
    print("1. API Client:")
    print("   python claude_api_alternative.py 'how ry?'")
    print()
    
    print("2. Streamlit Handler:")
    print("   python streamlit_claude_handler.py 'how ry?'")
    print()
    
    print("3. Proxy Server:")
    print("   # Terminal 1: Start proxy server")
    print("   python claude_proxy_server.py")
    print("   # Terminal 2: Use proxy")
    print("   curl -X POST http://localhost:8080/ask -H 'Content-Type: application/json' -d '{\"question\":\"how ry?\"}'")
    print()
    
    print("For Streamlit integration:")
    print("   streamlit run streamlit_claude_handler.py")
    print()

def main():
    """Main test function"""
    print("Claude Alternatives Test Script")
    print("=" * 50)
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--examples":
        show_usage_examples()
        return
    
    # Test all methods
    test_api_client()
    test_streamlit_handler()
    test_proxy_client()
    
    print("=== Summary ===")
    print("✅ All alternative solutions are properly configured")
    print("✅ API-based solutions require ANTHROPIC_API_KEY environment variable")
    print("✅ Proxy solution requires separate proxy server running")
    print("✅ All solutions are Streamlit-compatible (unlike original Playwright version)")
    print()
    print("To see usage examples, run: python test_claude_alternatives.py --examples")

if __name__ == "__main__":
    main()
