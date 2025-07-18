#!/usr/bin/env python3
"""
test_ask_claude.py - Test script for ask_claude.py
"""

import subprocess
import sys
import os

def test_ask_claude():
    """Test the ask_claude.py script with various inputs"""
    
    print("🧪 Testing ask_claude.py script...")
    
    # Test 1: No arguments
    print("\n📋 Test 1: No arguments")
    try:
        result = subprocess.run([sys.executable, "ask_claude.py"], 
                              capture_output=True, text=True, timeout=10)
        print(f"Exit code: {result.returncode}")
        print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    # Test 2: Empty question
    print("\n📋 Test 2: Empty question")
    try:
        result = subprocess.run([sys.executable, "ask_claude.py", ""], 
                              capture_output=True, text=True, timeout=10)
        print(f"Exit code: {result.returncode}")
        print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    # Test 3: Valid question (but will likely fail without Chrome debug)
    print("\n📋 Test 3: Valid question")
    try:
        result = subprocess.run([sys.executable, "ask_claude.py", "What is 2+2?"], 
                              capture_output=True, text=True, timeout=30)
        print(f"Exit code: {result.returncode}")
        print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
    except Exception as e:
        print(f"❌ Test failed: {e}")

def show_usage_examples():
    """Show usage examples for ask_claude.py"""
    print("\n📖 Usage Examples:")
    print("=" * 50)
    print("1. Simple question:")
    print('   python ask_claude.py "What is the weather today?"')
    print()
    print("2. Multi-word question:")
    print('   python ask_claude.py "Explain quantum computing in simple terms"')
    print()
    print("3. Question with quotes:")
    print('   python ask_claude.py "What does \\"hello world\\" mean in programming?"')
    print()
    print("4. Long question:")
    print('   python ask_claude.py "Can you help me understand the difference between machine learning and artificial intelligence?"')
    print("=" * 50)

if __name__ == "__main__":
    print("🚀 ask_claude.py Test Suite")
    print("=" * 40)
    
    # Check if ask_claude.py exists
    if not os.path.exists("ask_claude.py"):
        print("❌ ask_claude.py not found in current directory")
        sys.exit(1)
    
    # Check if pup_test_claude.py exists
    if not os.path.exists("pup_test_claude.py"):
        print("❌ pup_test_claude.py not found in current directory")
        print("💡 Make sure pup_test_claude.py is in the same directory")
        sys.exit(1)
    
    print("✅ Required files found")
    
    # Run tests
    test_ask_claude()
    
    # Show usage examples
    show_usage_examples()
    
    print("\n🏁 Test suite completed!")
    print("\n💡 To use ask_claude.py with a real Chrome instance:")
    print("1. Start Chrome with debug enabled:")
    print("   chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug")
    print("2. Navigate to claude.ai in that Chrome instance")
    print("3. Run: python ask_claude.py \"Your question here\"")
