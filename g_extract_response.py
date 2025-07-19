import websocket
import json
import re

# WebSocket URL from the provided JSON
ws_url = "ws://localhost:9222/devtools/page/26F411DF5B6CF6C6EA8CB688C5E84F5F"

# Initialize WebSocket connection
ws = websocket.create_connection(ws_url)

def send_cdp_command(method, params, command_id):
    command = {"id": command_id, "method": method, "params": params}
    ws.send(json.dumps(command))
    
    while True:
        response = json.loads(ws.recv())
        if 'id' in response and response['id'] == command_id:
            return response
        elif 'method' in response:
            continue

def find_grok_response():
    """Find Grok's response using JavaScript evaluation"""
    print("🔍 SEARCHING FOR GROK'S RESPONSE...")
    
    # Use JavaScript to search for the response text directly
    js_code = """
    (function() {
        // Look for text that contains "Hi" or "Nice to hear"
        const allElements = document.querySelectorAll('*');
        const responses = [];
        
        for (let element of allElements) {
            const text = element.textContent || '';
            
            // Look for the specific response we saw in the screenshot
            if (text.includes('Hi! Nice to hear from you') || 
                text.includes('Nice to hear from you') ||
                text.includes('Hi!') && text.length < 100) {
                responses.push({
                    text: text.trim(),
                    tagName: element.tagName,
                    className: element.className
                });
            }
        }
        
        return responses;
    })()
    """
    
    response = send_cdp_command(
        "Runtime.evaluate",
        {
            "expression": js_code,
            "returnByValue": True
        },
        100
    )
    
    if 'result' in response and 'result' in response['result']:
        results = response['result']['value']
        
        if results:
            print(f"🎉 FOUND {len(results)} POTENTIAL RESPONSES:")
            for i, result in enumerate(results, 1):
                text = result['text']
                tag = result['tagName']
                className = result['className']
                
                print(f"\nResponse {i}:")
                print(f"  Tag: {tag}")
                print(f"  Class: {className}")
                print(f"  Text: '{text}'")
                
                # Check if this looks like Grok's response
                if ('Hi!' in text and 'Nice to hear' in text and 
                    len(text) < 200 and 'Hello, Grok!' not in text):
                    print(f"  ⭐ THIS LOOKS LIKE GROK'S RESPONSE!")
        else:
            print("❌ No responses found with JavaScript search")
            
            # Try a broader search
            print("\n🔍 Trying broader search for any 'Hi' text...")
            
            broader_js = """
            (function() {
                const allElements = document.querySelectorAll('*');
                const hiTexts = [];
                
                for (let element of allElements) {
                    const text = element.textContent || '';
                    if (text.includes('Hi') && text.length < 500) {
                        hiTexts.push(text.trim());
                    }
                }
                
                return hiTexts.slice(0, 10); // Return first 10 matches
            })()
            """
            
            broader_response = send_cdp_command(
                "Runtime.evaluate",
                {
                    "expression": broader_js,
                    "returnByValue": True
                },
                101
            )
            
            if 'result' in broader_response and 'result' in broader_response['result']:
                broader_results = broader_response['result']['value']
                
                print(f"Found {len(broader_results)} texts containing 'Hi':")
                for text in broader_results:
                    if len(text) > 5:
                        print(f"  '{text[:100]}...'")

# Main execution
print("🚀 GROK RESPONSE EXTRACTOR")
print("=" * 40)

try:
    # Enable Runtime and DOM
    send_cdp_command("Runtime.enable", {}, 1)
    send_cdp_command("DOM.enable", {}, 2)
    send_cdp_command("DOM.getDocument", {}, 3)
    
    # Find the response
    find_grok_response()
    
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    ws.close()
    print("\n✅ Script completed!")
