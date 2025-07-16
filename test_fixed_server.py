import requests
import json
import time

def test_fixed_chatgpt_api():
    """Test the FIXED ChatGPT streaming API"""
    url = "http://127.0.0.1:8002/chatgpt"  # Note: port 8002 for fixed server
    
    # Test data
    test_message = {
        "message": "Hello! Can you tell me a short joke?",
        "timeout": 30
    }
    
    print("Testing FIXED ChatGPT Streaming API...")
    print(f"Sending message: {test_message['message']}")
    print("-" * 50)
    
    try:
        # Send POST request with streaming
        response = requests.post(
            url, 
            json=test_message, 
            stream=True,
            headers={"Content-Type": "application/json"},
            timeout=45  # Client timeout longer than server timeout
        )
        
        if response.status_code == 200:
            print("✅ Connection successful! Streaming response:")
            print("-" * 50)
            
            # Track previous content to show only incremental changes
            previous_content = ""
            response_started = False
            response_complete = False
            chunk_count = 0
            start_time = time.time()
            
            # Process streaming response
            for line in response.iter_lines():
                if line:
                    chunk_count += 1
                    elapsed = time.time() - start_time
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
                                print(f"\n✅ Response complete! ({len(content)} characters total)")
                                response_complete = True
                                break
                            elif status in ['timeout', 'error']:
                                print(f"\n❌ {status.upper()}: {content}")
                                response_complete = True
                                break
                                
                        except json.JSONDecodeError:
                            print(f"⚠️  Could not parse: {data_str}")
                
                # Safety timeout - stop after 40 seconds
                if time.time() - start_time > 40:
                    print(f"\n⏰ Client safety timeout after 40 seconds")
                    print(f"📊 Received {chunk_count} chunks")
                    if previous_content:
                        print(f"📝 Final content: {previous_content}")
                    break
            
            if not response_started:
                print("❌ No response started signal received")
            elif not response_complete:
                print("⚠️  Response may be incomplete (no completion signal received)")
                if previous_content:
                    print(f"📝 Partial content received ({len(previous_content)} chars):")
                    print(previous_content)
                    
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Make sure the FIXED server is running on http://127.0.0.1:8002")
        print("💡 Run: python chats_fixed.py")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_fixed_health_endpoints():
    """Test the health check endpoints for the fixed server"""
    print("\n" + "="*60)
    print("Testing FIXED Server Health Endpoints...")
    
    # Test root endpoint
    try:
        response = requests.get("http://127.0.0.1:8002/", timeout=5)
        if response.status_code == 200:
            print("✅ Root endpoint working:")
            print(f"   {response.json()}")
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
    
    # Test health endpoint
    try:
        response = requests.get("http://127.0.0.1:8002/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health endpoint working:")
            print(f"   {response.json()}")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")

if __name__ == "__main__":
    print("ChatGPT Streaming API FIXED Server Test Client")
    print("="*60)
    print("🔧 This tests the FIXED version running on port 8002")
    print("💡 Make sure to run: python chats_fixed.py first")
    
    # Test health endpoints first
    test_fixed_health_endpoints()
    
    # Test main API
    print("\n" + "="*60)
    test_fixed_chatgpt_api()
    
    print("\n" + "="*60)
    print("Test completed!")
