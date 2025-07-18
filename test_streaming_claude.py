#!/usr/bin/env python3
"""
Test script for the streaming Claude CDP functionality
"""

import subprocess
import sys
import time

def test_streaming_claude():
    """Test the streaming Claude script with a sample question"""
    
    print("🧪 Testing Streaming Claude CDP")
    print("=" * 40)
    
    # Test questions
    test_questions = [
        "Hello, how are you today?",
        "Tell me a short story about a robot",
        "Explain what Python is in simple terms"
    ]
    
    print("Available test questions:")
    for i, question in enumerate(test_questions, 1):
        print(f"{i}. {question}")
    
    print("\nChoose a question (1-3) or press Enter for question 1:")
    choice = input().strip()
    
    if choice == "2":
        question = test_questions[1]
    elif choice == "3":
        question = test_questions[2]
    else:
        question = test_questions[0]
    
    print(f"\n🚀 Running streaming test with: '{question}'")
    print("=" * 50)
    
    try:
        # Run the streaming script
        result = subprocess.run([
            sys.executable, 
            "claude_simple_cdp_streaming.py", 
            question
        ], capture_output=False, text=True)
        
        if result.returncode == 0:
            print("\n✅ Test completed successfully!")
        else:
            print(f"\n❌ Test failed with return code: {result.returncode}")
            
    except FileNotFoundError:
        print("❌ Error: claude_simple_cdp_streaming.py not found")
        print("Make sure the streaming script is in the current directory")
    except Exception as e:
        print(f"❌ Error running test: {e}")

def main():
    print("🔧 Claude Streaming CDP Test Suite")
    print("=" * 40)
    print()
    
    # Check if the streaming script exists
    try:
        with open("claude_simple_cdp_streaming.py", 'r') as f:
            pass
        print("✅ Streaming script found")
    except FileNotFoundError:
        print("❌ claude_simple_cdp_streaming.py not found!")
        print("Please make sure the streaming script is in the current directory")
        return
    
    print()
    print("📋 Prerequisites:")
    print("1. Chrome running with debug port: chrome --remote-debugging-port=9222")
    print("2. Claude.ai tab open and logged in")
    print("3. On a conversation page (not the main page)")
    print()
    
    input("Press Enter when ready to test...")
    print()
    
    test_streaming_claude()

if __name__ == "__main__":
    main()
