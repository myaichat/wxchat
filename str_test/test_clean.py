import requests
import json
import time

def test_chatgpt_api():
    """Test the ChatGPT streaming API with clean output"""
    url = "http://127.0.0.1:8002/chatgpt"
    
    # Test data
    test_message = {
        "message": "Hello! Can you tell ne about dbt?",
        "timeout": 30
    }
    
    print("ChatGPT Streaming API Test")
    print("=" * 40)
    print(f"Message: {test_message['message']}")
    print("-" * 40)
    
    try:
        # Send POST request with streaming
        response = requests.post(
            url, 
            json=test_message, 
            stream=True,
            headers={"Content-Type": "application/json"},
            timeout=45
        )
        
        if response.status_code == 200:
            print("🚀 Response:")
            print()
            
            # Track previous content to show only incremental changes
            previous_content = ""
            response_started = False
            response_complete = False
            start_time = time.time()
            
            # Process streaming response
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]  # Remove 'data: ' prefix
                        try:
                            data = json.loads(data_str)
                            status = data.get('status', '')
                            content = data.get('content', '')
                            
                            if status == 'started':
                                response_started = True
                            elif status == 'streaming':
                                # Show only the new part (incremental)
                                if len(content) > len(previous_content):
                                    new_chunk = content[len(previous_content):]
                                    print(new_chunk, end='', flush=True)
                                    previous_content = content
                            elif status == 'complete':
                                # Show any final chunk
                                if len(content) > len(previous_content):
                                    new_chunk = content[len(previous_content):]
                                    print(new_chunk, end='', flush=True)
                                
                                elapsed = time.time() - start_time
                                print(f"\n\n✅ Complete ({len(content)} chars, {elapsed:.1f}s)")
                                response_complete = True
                                break
                            elif status in ['timeout', 'error']:
                                print(f"\n❌ {status.upper()}: {content}")
                                response_complete = True
                                break
                                
                        except json.JSONDecodeError:
                            continue
                
                # Safety timeout
                if time.time() - start_time > 40:
                    print(f"\n⏰ Timeout after 40 seconds")
                    if previous_content:
                        print(f"Partial response: {previous_content}")
                    break
            
            if not response_started:
                print("❌ No response received")
            elif not response_complete:
                print(f"\n⚠️  Response incomplete")
                if previous_content:
                    print(f"Partial content: {previous_content}")
                    
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Make sure the server is running:")
        print("   python chats_fixed.py")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_health():
    """Quick health check"""
    try:
        response = requests.get("http://127.0.0.1:8002/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server: {data.get('service', 'Unknown')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server not responding: {e}")
        return False

if __name__ == "__main__":
    print("ChatGPT Streaming API - Clean Test Client")
    print("=" * 50)
    
    # Quick health check
    if test_health():
        print()
        test_chatgpt_api()
    else:
        print("\n💡 Start the server first: python chats_fixed.py")
    
    print("\n" + "=" * 50)
