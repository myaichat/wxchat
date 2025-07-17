#!/usr/bin/env python3
"""
Test script to demonstrate the logging functionality of ask_chatgpt.py.
This script tests the ask_chatgpt.py client and shows how logs are created.
"""

import subprocess
import os
import time
import json

def test_ask_chatgpt_logging():
    """Test the ask_chatgpt.py client with logging functionality"""
    
    # Test message
    test_message = "What is JavaScript? Give me a brief overview."
    
    print("=" * 60)
    print("TESTING ASK_CHATGPT.PY WITH LOGGING")
    print("=" * 60)
    print(f"Test message: {test_message}")
    print("-" * 60)
    
    # Check if logs directory exists before test
    logs_before = set()
    if os.path.exists("logs"):
        logs_before = set(os.listdir("logs"))
    
    try:
        print("Running ask_chatgpt.py...")
        print("=" * 40)
        
        # Run ask_chatgpt.py with the test message
        result = subprocess.run([
            "python", "ask_chatgpt.py", test_message
        ], capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        if result.returncode == 0:
            print("✅ ask_chatgpt.py executed successfully")
            print("\nOutput:")
            print(result.stdout)
            
            if result.stderr:
                print("\nStderr:")
                print(result.stderr)
        else:
            print(f"❌ ask_chatgpt.py failed with return code: {result.returncode}")
            print("Stdout:", result.stdout)
            print("Stderr:", result.stderr)
            return
            
        print("=" * 40)
        
        # Check for new log files
        time.sleep(1)  # Give time for file to be written
        
        if os.path.exists("logs"):
            logs_after = set(os.listdir("logs"))
            new_logs = logs_after - logs_before
            
            # Filter for ask_chatgpt logs
            ask_chatgpt_logs = [log for log in new_logs if log.startswith("ask_chatgpt_chat_session_")]
            
            if ask_chatgpt_logs:
                print(f"✅ New ask_chatgpt log file created: {ask_chatgpt_logs[0]}")
                
                # Show log content
                log_file = ask_chatgpt_logs[0]
                with open(f"logs/{log_file}", 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
                    
                print("\n📄 Log file contents:")
                print(f"  Timestamp: {log_data['timestamp']}")
                print(f"  Question: {log_data['question']}")
                print(f"  Answer length: {len(log_data['answer'])} characters")
                print(f"  Model: {log_data['model']}")
                
                # Show first 200 chars of answer
                if log_data['answer']:
                    preview = log_data['answer'][:200]
                    if len(log_data['answer']) > 200:
                        preview += "..."
                    print(f"  Answer preview: {preview}")
            else:
                print("⚠️  No new ask_chatgpt log file detected")
                if new_logs:
                    print(f"   Other new logs found: {list(new_logs)}")
        else:
            print("⚠️  Logs directory not found")
            
    except subprocess.TimeoutExpired:
        print("❌ Timeout: ask_chatgpt.py took too long to respond")
    except FileNotFoundError:
        print("❌ Error: ask_chatgpt.py not found or Python not in PATH")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("=" * 60)

def show_log_summary():
    """Show summary of all log files"""
    if not os.path.exists("logs"):
        print("No logs directory found")
        return
        
    log_files = os.listdir("logs")
    if not log_files:
        print("No log files found")
        return
        
    print("\n" + "=" * 60)
    print("LOG FILES SUMMARY")
    print("=" * 60)
    
    server_logs = [f for f in log_files if f.startswith("server_chat_session_")]
    ask_chatgpt_logs = [f for f in log_files if f.startswith("ask_chatgpt_chat_session_")]
    other_logs = [f for f in log_files if not f.startswith(("server_chat_session_", "ask_chatgpt_chat_session_"))]
    
    print(f"📊 Server logs (streaming_server.py): {len(server_logs)}")
    for log in sorted(server_logs)[-3:]:  # Show last 3
        print(f"   - {log}")
    if len(server_logs) > 3:
        print(f"   ... and {len(server_logs) - 3} more")
        
    print(f"📊 Ask ChatGPT logs (ask_chatgpt.py): {len(ask_chatgpt_logs)}")
    for log in sorted(ask_chatgpt_logs)[-3:]:  # Show last 3
        print(f"   - {log}")
    if len(ask_chatgpt_logs) > 3:
        print(f"   ... and {len(ask_chatgpt_logs) - 3} more")
        
    if other_logs:
        print(f"📊 Other logs: {len(other_logs)}")
        for log in sorted(other_logs)[-3:]:  # Show last 3
            print(f"   - {log}")
        if len(other_logs) > 3:
            print(f"   ... and {len(other_logs) - 3} more")
    
    print("=" * 60)

if __name__ == "__main__":
    test_ask_chatgpt_logging()
    show_log_summary()
