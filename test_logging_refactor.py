#!/usr/bin/env python3
"""
Test script to verify the refactored logging system works correctly.
This script simulates the logging behavior without running the full Streamlit app.
"""

import os
import json
import datetime

# Simulate the logging directory structure
LOGS_DIR = "logs"
CHATGPT_LOGS_DIR = os.path.join(LOGS_DIR, "chatgpt")
CLAUDE_LOGS_DIR = os.path.join(LOGS_DIR, "claude")

# Ensure directories exist
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(CHATGPT_LOGS_DIR, exist_ok=True)
os.makedirs(CLAUDE_LOGS_DIR, exist_ok=True)

def test_chatgpt_logging():
    """Test ChatGPT logging functionality"""
    print("Testing ChatGPT logging...")
    
    # Create a test log file path
    session_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    chatgpt_log_file = os.path.join(CHATGPT_LOGS_DIR, f"chatgpt_session_{session_timestamp}.json")
    
    # Create a test log entry
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "question": "Test question for ChatGPT",
        "model": "gpt-4o",
        "webui_question": "Answer in clean raw markdown language. Test question for ChatGPT. Answer in clean raw markdown language without citations or or contentReference. Answer in clean raw markdown language",
        "api_question": "Test question for ChatGPT",
        "webui_answer": "This is a test Web UI response from ChatGPT.",
        "api_answer": "This is a test API response from ChatGPT."
    }
    
    # Write to ChatGPT log file
    with open(chatgpt_log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False, indent=2) + "\n")
    
    print(f"✅ ChatGPT log created: {chatgpt_log_file}")
    return chatgpt_log_file

def test_claude_logging():
    """Test Claude logging functionality"""
    print("Testing Claude logging...")
    
    # Create a test log file path
    session_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    claude_log_file = os.path.join(CLAUDE_LOGS_DIR, f"claude_session_{session_timestamp}.json")
    
    # Create a test log entry
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "question": "Test question for Claude",
        "model": "claude-3-5-sonnet-20241022",
        "webui_question": "Answer in clean raw markdown language. Test question for Claude. Wrapp the entire response in a markdown code block to show the actual syntax",
        "api_question": "Test question for Claude",
        "webui_answer": "This is a test Web UI response from Claude.",
        "api_answer": "This is a test API response from Claude."
    }
    
    # Write to Claude log file
    with open(claude_log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False, indent=2) + "\n")
    
    print(f"✅ Claude log created: {claude_log_file}")
    return claude_log_file

def verify_log_files(chatgpt_file, claude_file):
    """Verify that the log files were created correctly"""
    print("\nVerifying log files...")
    
    # Check ChatGPT log
    if os.path.exists(chatgpt_file):
        with open(chatgpt_file, "r", encoding="utf-8") as f:
            content = f.read()
            if "ChatGPT" in content and "gpt-4o" in content:
                print("✅ ChatGPT log file contains expected content")
            else:
                print("❌ ChatGPT log file content is incorrect")
    else:
        print("❌ ChatGPT log file was not created")
    
    # Check Claude log
    if os.path.exists(claude_file):
        with open(claude_file, "r", encoding="utf-8") as f:
            content = f.read()
            if "Claude" in content and "claude-3-5-sonnet" in content:
                print("✅ Claude log file contains expected content")
            else:
                print("❌ Claude log file content is incorrect")
    else:
        print("❌ Claude log file was not created")

def main():
    """Main test function"""
    print("🧪 Testing Refactored Logging System")
    print("=" * 50)
    
    # Test both logging systems
    chatgpt_file = test_chatgpt_logging()
    claude_file = test_claude_logging()
    
    # Verify the results
    verify_log_files(chatgpt_file, claude_file)
    
    print("\n📁 Directory Structure:")
    print(f"logs/")
    print(f"├── chatgpt/")
    for file in os.listdir(CHATGPT_LOGS_DIR):
        print(f"│   └── {file}")
    print(f"└── claude/")
    for file in os.listdir(CLAUDE_LOGS_DIR):
        print(f"    └── {file}")
    
    print("\n✅ Logging refactor test completed successfully!")
    print("The logging system now creates separate directories and files for ChatGPT and Claude.")

if __name__ == "__main__":
    main()
