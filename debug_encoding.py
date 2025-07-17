#!/usr/bin/env python
"""
Debug script to test encoding issues
"""

import sys
import io

# Test the same console setup as ask_chatgpt.py
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def test_print(text):
    """Test different printing approaches"""
    print("=== Testing original text ===")
    print(repr(text))
    
    print("\n=== Testing direct print ===")
    try:
        print(text)
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Testing character by character ===")
    try:
        for char in text:
            print(char, end='', flush=True)
        print()  # newline
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Testing with encode/decode ===")
    try:
        safe_text = text.encode('utf-8', errors='replace').decode('utf-8')
        print(safe_text)
    except Exception as e:
        print(f"Error: {e}")

# Test the problematic text
test_text = """## 🔑 Key Principles

- **Memory Safety**: Achieved through ownership, borrowing, and lifetimes  
- **Concurrency**: Makes it easy and safe to write multithreaded code  
- **Zero-Cost Abstractions**: High-level constructs with no runtime overhead  
- **Performance**: Comparable to C and C++, ideal for system-level programming  
- **Tooling**: Strong development tools like `cargo`, `rustfmt`, and `clippy`"""

if __name__ == "__main__":
    test_print(test_text)
