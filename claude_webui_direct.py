"""
Direct replacement for: python '.\chat_handlers\claude_streaming_chat.py' 'how ry?'
Uses web UI only, no API keys required.
"""

import requests
import subprocess
import sys
import time
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: python claude_webui_direct.py 'your question'")
        return
    
    question = sys.argv[1]
    
    # Check Chrome debug
    try:
        requests.get("http://localhost:9222/json", timeout=2)
    except:
        print("Start Chrome with: chrome --remote-debugging-port=9222 --user-data-dir=C:\\temp\\chrome-debug")
        print("Then open claude.ai and login")
        return
    
    # Start proxy server
    proxy = subprocess.Popen([sys.executable, "claude_proxy_server.py"], 
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for proxy
    for i in range(10):
        try:
            time.sleep(1)
            requests.get("http://localhost:8080/health", timeout=1)
            break
        except:
            continue
    else:
        proxy.terminate()
        print("Failed to start proxy server")
        return
    
    # Ask question
    try:
        response = requests.post("http://localhost:8080/ask", 
                               json={"question": question}, timeout=60)
        if response.status_code == 200:
            print(response.json().get("response", "No response"))
        else:
            print(f"Error: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        proxy.terminate()

if __name__ == "__main__":
    main()
