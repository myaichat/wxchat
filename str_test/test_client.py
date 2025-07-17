import requests
import json
import time

def test_chatgpt_api():
    """Test the ChatGPT streaming API"""
    url = "http://127.0.0.1:8001/chatgpt"
    
    # Test data
    test_message = {
        "message": "Hello! Can you tell me a short joke?",
        "timeout": 30
    }
    
    print("Testing ChatGPT Streaming API...")
    print(f"Sending message: {test_message['message']}")
    print("-" * 50)
    
    try:
        # Send POST request with streaming
        response = requests.post(
            url, 
            json=test_message, 
            stream=True,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("✅ Connection successful! Streaming response:")
            print("-" * 50)
            
            # Track previous content to show only incremental changes
            previous_content = ""
            
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
                                print("🚀 Response started streaming...")
                                print("📝 ", end='', flush=True)  # Start the streaming line
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
                                print(f"\n✅ Response complete! ({len(content)} characters total)")
                                break
                            elif status in ['timeout', 'error']:
                                print(f"\n❌ {status.upper()}: {content}")
                                break
                                
                        except json.JSONDecodeError:
                            print(f"⚠️  Could not parse: {data_str}")
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Make sure the server is running on http://127.0.0.1:8001")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_health_endpoints():
    """Test the health check endpoints"""
    print("\n" + "="*60)
    print("Testing Health Endpoints...")
    
    # Test root endpoint
    try:
        response = requests.get("http://127.0.0.1:8001/")
        if response.status_code == 200:
            print("✅ Root endpoint working:")
            print(f"   {response.json()}")
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
    
    # Test health endpoint
    try:
        response = requests.get("http://127.0.0.1:8001/health")
        if response.status_code == 200:
            print("✅ Health endpoint working:")
            print(f"   {response.json()}")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")

if __name__ == "__main__":
    print("ChatGPT Streaming API Test Client")
    print("="*60)
    
    # Test health endpoints first
    test_health_endpoints()
    
    # Test main API
    print("\n" + "="*60)
    test_chatgpt_api()
    
    print("\n" + "="*60)
    print("Test completed!")
