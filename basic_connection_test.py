import json
import requests
from websocket import create_connection

def test_basic_connection():
    """Test basic WebSocket connection to Grok tab."""
    try:
        # Get Chrome tabs
        response = requests.get("http://localhost:9222/json")
        tabs = response.json()
        
        print("Available Chrome tabs:")
        grok_tab = None
        for i, tab in enumerate(tabs):
            print(f"{i+1}. {tab.get('title', 'No title')} - {tab.get('url', 'No URL')}")
            if "grok.com" in tab.get("url", ""):
                grok_tab = tab
                print(f"   ✓ Found Grok tab")
        
        if not grok_tab:
            print("No Grok tab found!")
            return
        
        print(f"\nGrok tab details:")
        print(f"  Title: {grok_tab.get('title')}")
        print(f"  URL: {grok_tab.get('url')}")
        print(f"  WebSocket URL: {grok_tab.get('webSocketDebuggerUrl')}")
        
        # Test WebSocket connection
        print(f"\nTesting WebSocket connection...")
        ws_url = grok_tab["webSocketDebuggerUrl"]
        
        try:
            ws = create_connection(ws_url, timeout=5)
            print("✓ WebSocket connection successful")
            
            # Send a simple ping-like command
            test_command = {
                "id": 1,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": "1+1",
                    "returnByValue": True
                }
            }
            
            print("Sending test command...")
            ws.send(json.dumps(test_command))
            
            # Try to receive response with short timeout
            ws.settimeout(3)
            try:
                response = ws.recv()
                print(f"✓ Received response: {response}")
                result = json.loads(response)
                if result.get("result", {}).get("result", {}).get("value") == 2:
                    print("✓ JavaScript execution working!")
                else:
                    print("? Unexpected response format")
            except Exception as e:
                print(f"✗ No response received: {e}")
            
            ws.close()
            
        except Exception as e:
            print(f"✗ WebSocket connection failed: {e}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_basic_connection()
