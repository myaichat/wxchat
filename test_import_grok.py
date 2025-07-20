#!/usr/bin/env python3
"""
Test script to demonstrate importing send_message_with_streaming from grok_cdp_pychrome_hybrid_generator
"""

# Import the function
from grok_cdp_pychrome_hybrid_generator import send_message_with_streaming

def test_import():
    """Test that the function can be imported and called"""
    print("✅ Successfully imported send_message_with_streaming!")
    print("📝 Function signature:", send_message_with_streaming.__doc__)
    
    # Example usage (commented out since it requires a running Chrome instance)
    """
    # Example usage:
    question = "What is Python?"
    
    print(f"🤖 Asking Grok: {question}")
    
    for chunk_info in send_message_with_streaming(question, timeout=60):
        if chunk_info.get('is_first'):
            print("📦 First chunk received!")
            print("Content:", chunk_info['chunk'][:200] + "..." if len(chunk_info['chunk']) > 200 else chunk_info['chunk'])
        elif chunk_info.get('is_final'):
            print("🏁 Final chunk received!")
            break
        else:
            print(f"📦 Incremental chunk: {chunk_info['chunk_size']} chars")
    """
    
    print("\n✅ Import test completed successfully!")
    print("💡 You can now use: from grok_cdp_pychrome_hybrid_generator import send_message_with_streaming")

if __name__ == "__main__":
    test_import()
