#!/usr/bin/env python3
"""
Test script to demonstrate the logging functionality of the streaming server.
This script sends a test message to the server and shows how logs are created.
"""

import requests
import json
import time
import os

def test_streaming_with_logging():
    """Test the streaming server with logging functionality"""
    
    # Test message
    test_message = "What is Python? Give me a brief overview."
    
    print("=" * 60)
    print("TESTING STREAMING SERVER WITH LOGGING")
    print("=" * 60)
    print(f"Test message: {test_message}")
    print("-" * 60)
    
    # Check if logs directory exists before test
    logs_before = set()
    if os.path.exists("logs"):
        logs_before = set(os.listdir("logs"))
    
    try:
        # Send request to streaming server
        payload = {"message": test_message, "timeout": 60}
        
        print("Sending request to streaming server...")
        print("Streaming response:")
        print("-" * 40)
        
        with requests.post("http://localhost:8002/ask-chatgpt", json=payload, stream=True) as response:
            if response.status_code == 200:
                complete_response = ""
                
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            status = chunk.get("status", "")
                            content = chunk.get("content", "")
                            
                            if status == "started":
                                print("🚀 Response started streaming...")
                            elif status == "streaming":
                                # Show streaming progress (just dots to avoid clutter)
                                print(".", end="", flush=True)
                            elif status == "complete":
                                complete_response = content
                                print(f"\n✅ Response complete ({len(content)} chars)")
                                break
                            elif status == "error":
                                print(f"\n❌ Error: {content}")
                                break
                                
                        except json.JSONDecodeError:
                            continue
                            
                print("-" * 40)
                
                # Check for new log files
                time.sleep(1)  # Give time for file to be written
                
                if os.path.exists("logs"):
                    logs_after = set(os.listdir("logs"))
                    new_logs = logs_after - logs_before
                    
                    if new_logs:
                        print(f"✅ New log file created: {list(new_logs)[0]}")
                        
                        # Show log content
                        log_file = list(new_logs)[0]
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
                        print("⚠️  No new log file detected")
                else:
                    print("⚠️  Logs directory not found")
                    
            else:
                print(f"❌ Server error: {response.status_code}")
                print(response.text)
                
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Make sure the streaming server is running on port 8002")
        print("   Start it with: python streaming_server.py")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("=" * 60)

if __name__ == "__main__":
    test_streaming_with_logging()
