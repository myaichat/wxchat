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

def extract_all_text():
    """Extract all text and find the response"""
    print("🔍 EXTRACTING ALL PAGE TEXT...")
    
    # Simple approach - get all text content
    js_code = """
    document.body.innerText || document.body.textContent || '';
    """
    
    try:
        response = send_cdp_command(
            "Runtime.evaluate",
            {
                "expression": js_code,
                "returnByValue": True
            },
            100
        )
        
        print(f"Response structure: {response}")
        
        if 'result' in response:
            result = response['result']
            if 'value' in result:
                all_text = result['value']
                print(f"📄 Extracted {len(all_text)} characters of text")
                
                # Look for the response we saw in the screenshot
                if "Hi! Nice to hear from you" in all_text:
                    print("🎉 FOUND THE EXACT RESPONSE!")
                    
                    # Extract the context around it
                    pos = all_text.find("Hi! Nice to hear from you")
                    context_start = max(0, pos - 100)
                    context_end = min(len(all_text), pos + 100)
                    context = all_text[context_start:context_end]
                    
                    print(f"📝 Context around response:")
                    print(f"'{context}'")
                    
                    # Extract just the response
                    response_match = re.search(r'Hi! Nice to hear from you[!.]?', all_text)
                    if response_match:
                        print(f"\n⭐ GROK'S RESPONSE: '{response_match.group()}'")
                    
                elif "Nice to hear from you" in all_text:
                    print("🎯 FOUND PARTIAL RESPONSE!")
                    pos = all_text.find("Nice to hear from you")
                    context_start = max(0, pos - 50)
                    context_end = min(len(all_text), pos + 50)
                    context = all_text[context_start:context_end]
                    print(f"📝 Context: '{context}'")
                    
                elif "Hi!" in all_text:
                    print("🔍 FOUND 'Hi!' - searching for full response...")
                    
                    # Find all instances of "Hi!"
                    hi_positions = []
                    start = 0
                    while True:
                        pos = all_text.find("Hi!", start)
                        if pos == -1:
                            break
                        hi_positions.append(pos)
                        start = pos + 1
                    
                    print(f"Found {len(hi_positions)} instances of 'Hi!'")
                    
                    for i, pos in enumerate(hi_positions):
                        context_start = max(0, pos - 30)
                        context_end = min(len(all_text), pos + 50)
                        context = all_text[context_start:context_end]
                        print(f"  Hi! #{i+1}: '{context}'")
                        
                        # Check if this looks like the response
                        if "Nice" in context or "hear" in context:
                            print(f"    ⭐ THIS MIGHT BE GROK'S RESPONSE!")
                
                else:
                    print("❌ Could not find the response text")
                    print(f"📝 First 500 characters of page text:")
                    print(f"'{all_text[:500]}...'")
                    
                    # Search for any greeting-like text
                    greetings = re.findall(r'\b(Hi|Hello|Hey|Greetings)[^.!?]*[.!?]', all_text, re.IGNORECASE)
                    if greetings:
                        print(f"\n🔍 Found {len(greetings)} greeting-like texts:")
                        for greeting in greetings[:5]:
                            print(f"  '{greeting}'")
            else:
                print(f"❌ No 'value' in result: {result}")
        else:
            print(f"❌ No 'result' in response: {response}")
            
    except Exception as e:
        print(f"❌ Error in JavaScript evaluation: {e}")
        
        # Fallback - try DOM approach
        print("\n🔄 Trying DOM fallback approach...")
        try:
            html_response = send_cdp_command("DOM.getOuterHTML", {"nodeId": 1}, 200)
            if 'result' in html_response and 'outerHTML' in html_response['result']:
                html = html_response['result']['outerHTML']
                
                if "Hi! Nice to hear from you" in html:
                    print("🎉 FOUND RESPONSE IN HTML!")
                    # Extract the text around it
                    pos = html.find("Hi! Nice to hear from you")
                    context = html[max(0, pos-200):pos+200]
                    print(f"HTML context: {context}")
                else:
                    print("❌ Response not found in HTML either")
        except Exception as e2:
            print(f"❌ DOM fallback also failed: {e2}")

# Main execution
print("🚀 FINAL GROK RESPONSE EXTRACTOR")
print("=" * 45)

try:
    # Enable Runtime
    send_cdp_command("Runtime.enable", {}, 1)
    
    # Extract text
    extract_all_text()
    
except Exception as e:
    print(f"❌ Main error: {e}")
finally:
    ws.close()
    print("\n✅ Script completed!")
