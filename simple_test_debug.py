import asyncio
import websockets
import json

async def debug_message_sending():
    """Debug the message sending process step by step"""
    ws_url = "ws://localhost:9222/devtools/page/88E0A660C0870B92DD1E7248EDABA645"
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ Connected to WebSocket")
            
            # Enable Runtime domain
            await websocket.send(json.dumps({
                "id": 1,
                "method": "Runtime.enable"
            }))
            
            # Wait for response
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                if data.get("id") == 1:
                    print("✅ Runtime domain enabled")
                    break
            
            # Simple message sending test
            test_message = "Hello! Can you tell me a short joke?"
            
            simple_js = f'''
                (function() {{
                    console.log("🔍 Starting simple message test");
                    
                    // Find textarea
                    const textarea = document.querySelector('textarea[placeholder*="Message"]') || 
                                   document.querySelector('textarea') ||
                                   document.querySelector('div[contenteditable="true"]');
                    
                    if (!textarea) {{
                        console.log("❌ No textarea found");
                        return "No textarea found";
                    }}
                    
                    console.log("✅ Found textarea:", textarea.tagName, textarea.placeholder || textarea.contentEditable);
                    
                    // Clear and set message
                    if (textarea.contentEditable === "true") {{
                        textarea.innerHTML = "";
                        textarea.focus();
                        textarea.innerHTML = "{test_message}";
                    }} else {{
                        textarea.value = "";
                        textarea.focus();
                        textarea.value = "{test_message}";
                    }}
                    
                    console.log("✅ Message set in textarea");
                    
                    // Trigger input events
                    textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    
                    // Find send button
                    const sendButton = document.querySelector('button[data-testid="send-button"]') ||
                                     document.querySelector('button[aria-label*="Send"]') ||
                                     document.querySelector('button[type="submit"]');
                    
                    if (!sendButton) {{
                        console.log("❌ No send button found");
                        return "No send button found";
                    }}
                    
                    console.log("✅ Found send button:", sendButton.tagName, sendButton.disabled);
                    
                    if (sendButton.disabled) {{
                        console.log("⚠️ Send button is disabled");
                        return "Send button disabled";
                    }}
                    
                    // Click send button
                    sendButton.click();
                    console.log("✅ Send button clicked");
                    
                    return "Message sent successfully";
                }})();
            '''
            
            print("🚀 Executing simple message test...")
            
            await websocket.send(json.dumps({
                "id": 2,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": simple_js,
                    "returnByValue": True
                }
            }))
            
            # Wait for result and console messages
            result_received = False
            timeout_count = 0
            
            while not result_received and timeout_count < 30:  # 30 second timeout
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    if data.get("id") == 2:
                        print(f"📋 Execution result: {data}")
                        result_received = True
                    elif data.get("method") == "Runtime.consoleAPICalled":
                        args = data.get("params", {}).get("args", [])
                        if args:
                            console_msg = args[0].get("value", "")
                            print(f"🖥️  Console: {console_msg}")
                            
                except asyncio.TimeoutError:
                    timeout_count += 1
                    print(f"⏱️  Waiting... ({timeout_count}s)")
                    continue
                except json.JSONDecodeError:
                    continue
            
            if not result_received:
                print("❌ Timeout waiting for execution result")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🔧 Simple Message Sending Debug Tool")
    print("="*50)
    asyncio.run(debug_message_sending())
