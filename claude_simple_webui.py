"""
Simple web UI alternative that directly replaces the original command.
This version works without API keys and provides clear setup instructions.
"""

import sys
import requests
import subprocess
import time
import os

def check_chrome_debug():
    """Check if Chrome debug port is accessible"""
    try:
        response = requests.get("http://localhost:9222/json", timeout=2)
        return response.status_code == 200
    except:
        return False

def show_setup_instructions():
    """Show setup instructions for Chrome debug mode"""
    print("=" * 60)
    print("SETUP REQUIRED - Chrome Debug Mode")
    print("=" * 60)
    print()
    print("To use this alternative (no API key required):")
    print()
    print("1. Close all Chrome instances")
    print("2. Start Chrome with debug mode:")
    print("   chrome --remote-debugging-port=9222 --user-data-dir=C:\\temp\\chrome-debug")
    print()
    print("3. In the debug Chrome:")
    print("   - Navigate to https://claude.ai")
    print("   - Log in to your account")
    print("   - Start a new conversation")
    print()
    print("4. Run this script again:")
    print(f"   python {sys.argv[0]} \"your question here\"")
    print()
    print("=" * 60)

def start_proxy_and_ask(question):
    """Start proxy server and ask question"""
    print("Starting proxy server...")
    
    # Start proxy server
    try:
        proxy_process = subprocess.Popen([
            sys.executable, "claude_proxy_server.py", 
            "--port", "8080", 
            "--debug-port", "9222"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for server to start
        server_started = False
        for i in range(15):  # Wait up to 15 seconds
            try:
                time.sleep(1)
                response = requests.get("http://localhost:8080/health", timeout=2)
                if response.status_code == 200:
                    print("✅ Proxy server started successfully")
                    server_started = True
                    break
            except:
                print(f"Waiting for proxy server... ({i+1}/15)")
                continue
        
        if not server_started:
            print("❌ Failed to start proxy server")
            proxy_process.terminate()
            return False
        
        # Ask question through proxy
        print(f"\nAsking Claude: {question}")
        print("Response:")
        print("-" * 40)
        
        try:
            response = requests.post(
                "http://localhost:8080/ask",
                json={"question": question, "streaming": False},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                claude_response = data.get("response")
                if claude_response:
                    print(claude_response)
                    print("-" * 40)
                    print(f"✅ Success! Got response ({len(claude_response)} characters)")
                    return True
                else:
                    print("❌ No response received from Claude")
                    return False
            else:
                print(f"❌ Proxy error: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"❌ Error communicating with proxy: {e}")
            return False
            
        finally:
            # Clean up proxy server
            print("\nStopping proxy server...")
            proxy_process.terminate()
            try:
                proxy_process.wait(timeout=5)
            except:
                proxy_process.kill()
            
    except Exception as e:
        print(f"❌ Error starting proxy server: {e}")
        return False

def main():
    """Main function"""
    print("Claude Web UI Alternative (No API Key Required)")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("Usage: python claude_simple_webui.py <question>")
        print("Example: python claude_simple_webui.py 'how ru?'")
        print()
        show_setup_instructions()
        return
    
    question = sys.argv[1]
    print(f"Question: {question}")
    print()
    
    # Check if Chrome debug is available
    if not check_chrome_debug():
        print("❌ Chrome debug port (9222) not accessible")
        print()
        show_setup_instructions()
        return
    
    print("✅ Chrome debug port accessible")
    
    # Check if required files exist
    if not os.path.exists("claude_proxy_server.py"):
        print("❌ claude_proxy_server.py not found")
        print("Make sure you have all the required files in the same directory")
        return
    
    print("✅ Proxy server file found")
    print()
    
    # Try to start proxy and ask question
    success = start_proxy_and_ask(question)
    
    if success:
        print("\n🎉 Successfully replaced the original Playwright command!")
        print("This method works in Streamlit environments.")
    else:
        print("\n❌ Failed to get response. Troubleshooting:")
        print("1. Make sure Claude.ai is open and logged in")
        print("2. Try asking a question manually in the browser first")
        print("3. Make sure you're on the conversation page, not the home page")

if __name__ == "__main__":
    main()
