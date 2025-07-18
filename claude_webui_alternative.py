"""
Web UI alternative to replace playwright-based Claude chat for Streamlit compatibility.
This uses the proxy server approach to maintain browser sessions without requiring API keys.
"""

import requests
import json
import subprocess
import time
import os
import sys
from typing import Optional

class ClaudeWebUIClient:
    """
    Client that uses the existing browser-based Claude interaction through a proxy server.
    This maintains the same web UI experience without requiring API keys.
    """
    
    def __init__(self, proxy_url: str = "http://localhost:8080", debug_port: int = 9222):
        self.proxy_url = proxy_url
        self.debug_port = debug_port
        self.proxy_process = None
    
    def start_proxy_server(self):
        """Start the proxy server if it's not running"""
        try:
            # Check if proxy is already running
            response = requests.get(f"{self.proxy_url}/health", timeout=2)
            if response.status_code == 200:
                print("Proxy server is already running")
                return True
        except:
            pass
        
        # Start the proxy server
        print("Starting proxy server...")
        try:
            self.proxy_process = subprocess.Popen([
                sys.executable, "claude_proxy_server.py", 
                "--port", "8080", 
                "--debug-port", str(self.debug_port)
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for server to start
            for i in range(10):  # Wait up to 10 seconds
                try:
                    time.sleep(1)
                    response = requests.get(f"{self.proxy_url}/health", timeout=2)
                    if response.status_code == 200:
                        print("Proxy server started successfully")
                        return True
                except:
                    continue
            
            print("Failed to start proxy server")
            return False
            
        except Exception as e:
            print(f"Error starting proxy server: {e}")
            return False
    
    def ask_claude_webui(self, question: str) -> Optional[str]:
        """
        Send question to Claude through web UI (via proxy server).
        
        Args:
            question (str): The question to ask
            
        Returns:
            str: Response or None if failed
        """
        try:
            response = requests.post(
                f"{self.proxy_url}/ask",
                json={"question": question, "streaming": False},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response")
            else:
                print(f"Proxy Error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.ConnectionError:
            print("Connection refused. Make sure:")
            print("1. Chrome is running with debug mode:")
            print(f"   chrome --remote-debugging-port={self.debug_port} --user-data-dir=/tmp/chrome-debug")
            print("2. Claude.ai is open in the browser")
            print("3. Proxy server is running")
            return None
        except Exception as e:
            print(f"Error calling proxy: {e}")
            return None
    
    def ask_claude_webui_streaming(self, question: str):
        """
        Stream Claude's response from web UI.
        
        Args:
            question (str): The question to ask
            
        Yields:
            str: Chunks of Claude's response
        """
        try:
            response = requests.post(
                f"{self.proxy_url}/ask_stream",
                json={"question": question},
                stream=True,
                timeout=60
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])
                                if 'chunk' in data:
                                    yield data['chunk']
                                elif 'error' in data:
                                    yield f"Error: {data['error']}"
                                    break
                                elif data.get('done'):
                                    break
                            except json.JSONDecodeError:
                                continue
            else:
                yield f"Proxy Error: {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            yield "Connection refused. Make sure Chrome debug and proxy server are running."
        except Exception as e:
            yield f"Error: {e}"
    
    def stop_proxy_server(self):
        """Stop the proxy server if we started it"""
        if self.proxy_process:
            self.proxy_process.terminate()
            self.proxy_process = None

def ask_claude_webui_simple(question: str, auto_start_proxy: bool = True) -> Optional[str]:
    """
    Simple function to ask Claude via web UI without API keys.
    
    Args:
        question (str): The question to ask
        auto_start_proxy (bool): Whether to auto-start proxy server
        
    Returns:
        str: Claude's response or None if failed
    """
    client = ClaudeWebUIClient()
    
    if auto_start_proxy:
        if not client.start_proxy_server():
            print("Failed to start proxy server. Please start manually:")
            print("python claude_proxy_server.py")
            return None
    
    try:
        return client.ask_claude_webui(question)
    finally:
        if auto_start_proxy:
            client.stop_proxy_server()

def setup_chrome_debug():
    """Show instructions for setting up Chrome debug mode"""
    print("=== Chrome Debug Setup ===")
    print("1. Close all Chrome instances")
    print("2. Start Chrome with debug mode:")
    print("   chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug")
    print("   (On Windows, use a different temp directory)")
    print("3. Navigate to https://claude.ai in the debug Chrome instance")
    print("4. Log in and start a conversation")
    print("5. Run this script again")
    print()

def main():
    """Main function for command line usage"""
    if len(sys.argv) < 2:
        print("Usage: python claude_webui_alternative.py <question>")
        print("Example: python claude_webui_alternative.py 'how ru?'")
        print()
        setup_chrome_debug()
        return
    
    question = sys.argv[1]
    print(f"Question: {question}")
    print()
    
    # Check if we should show setup instructions
    if "--setup" in sys.argv:
        setup_chrome_debug()
        return
    
    # Try to connect and ask question
    client = ClaudeWebUIClient()
    
    # First check if Chrome debug is available
    try:
        response = requests.get("http://localhost:9222/json", timeout=2)
        if response.status_code != 200:
            print("Chrome debug port not accessible.")
            setup_chrome_debug()
            return
    except:
        print("Chrome debug port not accessible.")
        setup_chrome_debug()
        return
    
    print("=== Attempting to use Web UI (no API key required) ===")
    
    # Try streaming response
    print("Streaming response:")
    full_response = ""
    
    for chunk in client.ask_claude_webui_streaming(question):
        if not chunk.startswith("Error:"):
            print(chunk, end='', flush=True)
            full_response += chunk
        else:
            print(f"\n{chunk}")
            # If streaming fails, try starting proxy server
            if "Connection refused" in chunk:
                print("\nTrying to start proxy server...")
                if client.start_proxy_server():
                    print("Proxy server started. Retrying...")
                    for chunk2 in client.ask_claude_webui_streaming(question):
                        if not chunk2.startswith("Error:"):
                            print(chunk2, end='', flush=True)
                            full_response += chunk2
                        else:
                            print(f"\n{chunk2}")
                            break
                client.stop_proxy_server()
            break
    
    print("\n")
    
    if full_response:
        print(f"✅ Successfully got response ({len(full_response)} characters)")
    else:
        print("❌ No response received")
        print("\nTroubleshooting:")
        print("1. Make sure Chrome is running with --remote-debugging-port=9222")
        print("2. Make sure Claude.ai is open and logged in")
        print("3. Try running: python claude_webui_alternative.py --setup")

if __name__ == "__main__":
    main()
