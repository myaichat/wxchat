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

print("🔍 DEBUGGING WHAT PAGE WE'RE CONNECTED TO...")

try:
    # Enable Runtime
    send_cdp_command("Runtime.enable", {}, 1)
    
    # Get page title and URL
    title_response = send_cdp_command(
        "Runtime.evaluate",
        {
            "expression": "document.title",
            "returnByValue": True
        },
        2
    )
    
    url_response = send_cdp_command(
        "Runtime.evaluate",
        {
            "expression": "window.location.href",
            "returnByValue": True
        },
        3
    )
    
    print(f"📄 Page Title: {title_response.get('result', {}).get('result', {}).get('value', 'Unknown')}")
    print(f"🌐 Page URL: {url_response.get('result', {}).get('result', {}).get('value', 'Unknown')}")
    
    # Look specifically for the chat response we saw in the screenshot
    search_response = send_cdp_command(
        "Runtime.evaluate",
        {
            "expression": """
            (function() {
                // Search for the exact text from the screenshot
                const bodyText = document.body.innerText || document.body.textContent || '';
                
                // Look for the response
                if (bodyText.includes('Hi! Nice to hear from you')) {
                    const pos = bodyText.indexOf('Hi! Nice to hear from you');
                    return {
                        found: true,
                        context: bodyText.substring(Math.max(0, pos - 100), pos + 100),
                        fullResponse: 'Hi! Nice to hear from you!'
                    };
                }
                
                // Look for partial matches
                if (bodyText.includes('Nice to hear from you')) {
                    const pos = bodyText.indexOf('Nice to hear from you');
                    return {
                        found: true,
                        context: bodyText.substring(Math.max(0, pos - 50), pos + 50),
                        fullResponse: 'Found partial: Nice to hear from you'
                    };
                }
                
                // Look for any "Hi!" 
                if (bodyText.includes('Hi!')) {
                    const pos = bodyText.indexOf('Hi!');
                    return {
                        found: true,
                        context: bodyText.substring(Math.max(0, pos - 30), pos + 70),
                        fullResponse: 'Found Hi! - checking context'
                    };
                }
                
                return {
                    found: false,
                    context: bodyText.substring(0, 200),
                    fullResponse: 'Not found'
                };
            })()
            """,
            "returnByValue": True
        },
        4
    )
    
    if 'result' in search_response and 'result' in search_response['result']:
        result = search_response['result']['value']
        
        if result['found']:
            print(f"\n🎉 FOUND RESPONSE!")
            print(f"📝 Context: '{result['context']}'")
            print(f"⭐ Response: '{result['fullResponse']}'")
        else:
            print(f"\n❌ Response not found")
            print(f"📝 Page starts with: '{result['context']}'")
    
    # Also check if we can find the chat interface elements
    chat_check = send_cdp_command(
        "Runtime.evaluate",
        {
            "expression": """
            (function() {
                const textareas = document.querySelectorAll('textarea');
                const chatElements = document.querySelectorAll('[class*="chat"], [class*="message"]');
                
                return {
                    textareas: textareas.length,
                    chatElements: chatElements.length,
                    hasGrokInTitle: document.title.toLowerCase().includes('grok'),
                    bodyLength: document.body.innerText.length
                };
            })()
            """,
            "returnByValue": True
        },
        5
    )
    
    if 'result' in chat_check and 'result' in chat_check['result']:
        chat_info = chat_check['result']['value']
        print(f"\n🔍 Page Analysis:")
        print(f"   Textareas found: {chat_info['textareas']}")
        print(f"   Chat elements: {chat_info['chatElements']}")
        print(f"   Has 'Grok' in title: {chat_info['hasGrokInTitle']}")
        print(f"   Body text length: {chat_info['bodyLength']} characters")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    ws.close()
    print("\n✅ Debug completed!")
