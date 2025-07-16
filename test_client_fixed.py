import requests
import json
import time
import signal
import sys

class TimeoutHandler:
    def __init__(self, timeout_seconds):
        self.timeout_seconds = timeout_seconds
        self.timed_out = False
    
    def timeout_handler(self, signum, frame):
        self.timed_out = True
        print(f"\n⏰ TIMEOUT: Client timed out after {self.timeout_seconds} seconds")
        print("🔄 This might indicate the server is not sending completion status properly")
        raise TimeoutError(f"Client timeout after {self.timeout_seconds} seconds")

def test_chatgpt_api_with_timeout():
    """Test the ChatGPT streaming API with better timeout handling"""
    url = "http://127.0.0.1:8001/chatgpt"
    
    # Test data
    test_message = {
        "message": "Hello! Can you tell me a short joke?",
        "timeout": 30
    }
    
    print("Testing ChatGPT Streaming API with Enhanced Timeout...")
    print(f"Sending message: {test_message['message']}")
    print("-" * 50)
    
    # Set up client-side timeout (longer than server timeout)
    client_timeout = 45  # 45 seconds client timeout vs 30 seconds server timeout
    timeout_handler = TimeoutHandler(client_timeout)
    
    # Set up signal handler for timeout
    signal.signal(signal.SIGALRM, timeout_handler.timeout_handler)
    signal.alarm(client_timeout)
    
    try:
        # Send POST request with streaming
        response = requests.post(
            url, 
            json=test_message, 
            stream=True,
            headers={"Content-Type": "application/json"},
            timeout=client_timeout  # requests timeout
        )
        
        if response.status_code == 200:
            print("✅ Connection successful! Streaming response:")
            print("-" * 50)
            
            # Track previous content to show only incremental changes
            previous_content = ""
            response_started = False
            response_complete = False
            chunk_count = 0
            last_activity_time = time.time()
            
            # Process streaming response
            for line in response.iter_lines():
                if timeout_handler.timed_out:
                    break
                    
                if line:
                    chunk_count += 1
                    last_activity_time = time.time()
                    line_str = line.decode('utf-8')
                    
                    print(f"[DEBUG] Chunk {chunk_count}: {line_str[:100]}...")  # Debug output
                    
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]  # Remove 'data: ' prefix
                        try:
                            data = json.loads(data_str)
                            status = data.get('status', '')
                            content = data.get('content', '')
                            
                            print(f"[DEBUG] Status: {status}, Content length: {len(content)}")
                            
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
                                
                        except json.JSONDecodeError as e:
                            print(f"⚠️  Could not parse JSON: {data_str}")
                            print(f"⚠️  JSON Error: {e}")
                
                # Check for inactivity timeout (no new chunks for 10 seconds)
                if time.time() - last_activity_time > 10:
                    print(f"\n⏰ No activity for 10 seconds, assuming response is complete")
                    print(f"📊 Received {chunk_count} chunks total")
                    if previous_content:
                        print(f"📝 Final content ({len(previous_content)} chars):")
                        print(previous_content)
                    break
            
            # Cancel the alarm
            signal.alarm(0)
            
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
            
    except TimeoutError:
        print("❌ Client timeout - this suggests the server is not properly completing the stream")
        print("💡 Possible causes:")
        print("   - WebSocket connection to Chrome DevTools is unstable")
        print("   - JavaScript observer is not detecting completion properly")
        print("   - Server-side timeout logic is not working")
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Make sure the server is running on http://127.0.0.1:8001")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Make sure to cancel any pending alarm
        signal.alarm(0)

def test_health_endpoints():
    """Test the health check endpoints"""
    print("\n" + "="*60)
    print("Testing Health Endpoints...")
    
    # Test root endpoint
    try:
        response = requests.get("http://127.0.0.1:8001/", timeout=5)
        if response.status_code == 200:
            print("✅ Root endpoint working:")
            print(f"   {response.json()}")
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
    
    # Test health endpoint
    try:
        response = requests.get("http://127.0.0.1:8001/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health endpoint working:")
            print(f"   {response.json()}")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")

def test_simple_non_streaming():
    """Test with a simple approach - just collect all data without parsing"""
    print("\n" + "="*60)
    print("Testing Simple Data Collection (No Parsing)...")
    
    url = "http://127.0.0.1:8001/chatgpt"
    test_message = {
        "message": "Hello! Can you tell me a short joke?",
        "timeout": 30
    }
    
    try:
        response = requests.post(url, json=test_message, stream=True, timeout=45)
        
        if response.status_code == 200:
            print("✅ Connection successful! Collecting raw data...")
            print("-" * 50)
            
            all_data = []
            start_time = time.time()
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    all_data.append(line_str)
                    print(f"[{time.time() - start_time:.1f}s] {line_str}")
                    
                # Stop after 30 seconds regardless
                if time.time() - start_time > 30:
                    print("\n⏰ Stopping after 30 seconds")
                    break
            
            print(f"\n📊 Collected {len(all_data)} lines total")
            
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("ChatGPT Streaming API Enhanced Test Client")
    print("="*60)
    
    # Test health endpoints first
    test_health_endpoints()
    
    # Test main API with timeout handling
    print("\n" + "="*60)
    test_chatgpt_api_with_timeout()
    
    # Test simple data collection
    test_simple_non_streaming()
    
    print("\n" + "="*60)
    print("Test completed!")
