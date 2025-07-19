import websocket
import json

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

print("🎯 EXTRACTING GROK'S RESPONSE FROM THE CHAT PAGE")
print("=" * 55)

try:
    # Enable Runtime
    send_cdp_command("Runtime.enable", {}, 1)
    
    # Simple direct search for the response
    response = send_cdp_command(
        "Runtime.evaluate",
        {
            "expression": "document.body.innerText",
            "returnByValue": True
        },
        2
    )
    
    # Try to extract the value properly
    if 'result' in response:
        result_obj = response['result']
        
        if 'result' in result_obj:
            inner_result = result_obj['result']
            
            if 'value' in inner_result:
                page_text = inner_result['value']
                print(f"📄 Successfully extracted {len(page_text)} characters of page text")
                
                # Search for the response
                if "Hi! Nice to hear from you" in page_text:
                    print("\n🎉 FOUND THE EXACT RESPONSE!")
                    
                    # Find the position and extract context
                    pos = page_text.find("Hi! Nice to hear from you")
                    start = max(0, pos - 50)
                    end = min(len(page_text), pos + 50)
                    context = page_text[start:end]
                    
                    print(f"📝 Context: '{context}'")
                    print(f"⭐ GROK'S RESPONSE: 'Hi! Nice to hear from you!'")
                    
                elif "Nice to hear from you" in page_text:
                    print("\n🎯 FOUND PARTIAL RESPONSE!")
                    pos = page_text.find("Nice to hear from you")
                    start = max(0, pos - 30)
                    end = min(len(page_text), pos + 30)
                    context = page_text[start:end]
                    print(f"📝 Context: '{context}'")
                    
                else:
                    print("\n❌ Response not found in page text")
                    print(f"📝 First 300 characters of page:")
                    print(f"'{page_text[:300]}...'")
                    
                    # Search for any "Hi" text
                    if "Hi" in page_text:
                        print(f"\n🔍 Found 'Hi' in the page - searching for context...")
                        hi_pos = page_text.find("Hi")
                        hi_context = page_text[max(0, hi_pos-20):hi_pos+80]
                        print(f"   Context around 'Hi': '{hi_context}'")
            else:
                print("❌ No 'value' in inner result")
        else:
            print("❌ No 'result' in result object")
    else:
        print("❌ No 'result' in response")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    ws.close()
    print("\n✅ Extraction completed!")
