import websocket
import json
import sys
import time
import re

# Check if question was provided as argument
if len(sys.argv) < 2:
    print("❌ Usage: python g_ask_grok.py \"Your question here\"")
    print("📝 Example: python g_ask_grok.py \"What is the weather like today?\"")
    sys.exit(1)

question = sys.argv[1]

# WebSocket URL from the provided JSON
ws_url = "ws://localhost:9222/devtools/page/26F411DF5B6CF6C6EA8CB688C5E84F5F"

def connect_websocket(ws_url):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            ws = websocket.create_connection(ws_url)
            print("✅ WebSocket connected")
            return ws
        except Exception as e:
            print(f"❌ WebSocket connection failed (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(2)
    raise Exception("Failed to connect to WebSocket after retries")

# Initialize WebSocket connection
ws = connect_websocket(ws_url)

def send_cdp_command(method, params, command_id):
    command = {"id": command_id, "method": method, "params": params}
    ws.send(json.dumps(command))
    
    while True:
        response = json.loads(ws.recv())
        if 'id' in response and response['id'] == command_id:
            return response
        elif 'method' in response:
            continue

def get_page_text():
    """Get all text content from the page"""
    response = send_cdp_command(
        "Runtime.evaluate",
        {
            "expression": "document.body.innerText",
            "returnByValue": True
        },
        999
    )
    
    if ('result' in response and 
        'result' in response['result'] and 
        'value' in response['result']['result']):
        return response['result']['result']['value']
    return ""

def send_message_to_grok(message):
    """Send a message to Grok via the textarea"""
    print(f"📤 Sending message: '{message}'")
    
    # Get document
    send_cdp_command("DOM.getDocument", {}, 1)
    
    # Find textarea
    textarea_response = send_cdp_command(
        "DOM.querySelector",
        {"nodeId": 1, "selector": "textarea"},
        2
    )
    
    if not textarea_response.get('result', {}).get('nodeId'):
        print("❌ Could not find textarea!")
        return False
    
    textarea_node_id = textarea_response['result']['nodeId']
    
    # Focus on textarea
    send_cdp_command("DOM.focus", {"nodeId": textarea_node_id}, 3)
    
    # Clear existing text
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Control"}, 4)
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyDown", "key": "KeyA"}, 5)
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyUp", "key": "KeyA"}, 6)
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Control"}, 7)
    
    # Type the message
    command_id = 8
    for char in message:
        send_cdp_command("Input.dispatchKeyEvent", {"type": "char", "text": char}, command_id)
        command_id += 1
        time.sleep(0.02)
    
    # Press Enter to send
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter"}, command_id)
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter"}, command_id + 1)
    
    print("✅ Message sent!")
    return True

def wait_for_response(timeout=120):  # Increase to 120 seconds
    """Wait for Grok's response and extract it"""
    print(f"⏳ Waiting for Grok's response (timeout: {timeout}s)...")
    
    # Get initial page content
    initial_text = get_page_text()
    initial_length = len(initial_text)
    
    start_time = time.time()
    last_length = initial_length
    stable_count = 0
    max_stable_time = 12  # Wait 12 seconds of stability
    
    while time.time() - start_time < timeout:
        time.sleep(2)  # Check every 2 seconds
        
        current_text = get_page_text()
        current_length = len(current_text)
        
        # Check if content has grown significantly
        if current_length > initial_length + 100:
            print(f"📈 Content increased: {initial_length} → {current_length}")
            
            # If content is still growing, reset stable count
            if current_length > last_length + 10:  # Even small growth resets stability
                stable_count = 0
                last_length = current_length
                print(f"🔄 Content still growing, resetting stability counter")
                continue
            else:
                stable_count += 1
                print(f"⏸️  Content stable for {stable_count * 2} seconds")
            
            # Wait for longer stability before extracting (12 seconds = 6 checks)
            if stable_count >= 6:
                print(f"✅ Content has been stable for {stable_count * 2} seconds, extracting response...")
                
                # Look for new content after our question
                if question in current_text:
                    # Find position of our question
                    question_pos = current_text.rfind(question)
                    
                    # Get text after our question
                    text_after_question = current_text[question_pos + len(question):]
                    
                    # Split into paragraphs (double newlines) or lines
                    paragraphs = text_after_question.split('\n\n')
                    if len(paragraphs) < 2:
                        paragraphs = text_after_question.split('\n')
                    
                    # Find the response content - RELAXED CRITERIA
                    response_parts = []
                    found_start = False
                    
                    for paragraph in paragraphs[:200]:  # Increase to 200 paragraphs
                        paragraph = paragraph.strip()
                        
                        # Skip empty content
                        if not paragraph:
                            continue
                            
                        # Skip known UI elements
                        if paragraph in ['How can Grok help?', 'DeepSearch', 'Think', 'Send', 'Upload', 'Grok 3', 'Upgrade to SuperGrok']:
                            if found_start:
                                print(f"🛑 Found end marker: '{paragraph}', stopping extraction")
                                break
                            continue
                        
                        # Skip time indicators and pure numbers
                        if re.match(r'^\d+\.?\d*[smh]$', paragraph) or paragraph.isdigit():
                            continue
                        
                        # Include more content, even shorter paragraphs
                        if len(paragraph) > 5:  # Lower threshold from 10
                            if not found_start:
                                print(f"🎯 Found response start: '{paragraph[:50]}...'")
                            found_start = True
                            response_parts.append(paragraph)
                    
                    if response_parts:
                        # Join with appropriate spacing
                        full_response = '\n\n'.join(response_parts)
                        
                        print(f"\n🎉 FOUND COMPLETE GROK RESPONSE!")
                        print(f"📊 Extracted {len(response_parts)} paragraphs, {len(full_response)} characters")
                        print(f"⭐ FIRST 500 CHARS OF RESPONSE: '{full_response[:500]}...'")
                        if len(full_response) > 5000:  # Warn if response is unusually long
                            print(f"⚠️ Response is very long ({len(full_response)} chars), possible truncation")
                        
                        return full_response
                    else:
                        print("⚠️  No valid response content found, continuing to wait...")
                        stable_count = 0  # Reset and keep waiting
            
            last_length = current_length
    
    print("⏰ Timeout reached - extracting whatever content is available")
    
    # Fallback: try to extract whatever we can find
    current_text = get_page_text()
    if question in current_text:
        question_pos = current_text.rfind(question)
        text_after = current_text[question_pos:question_pos + 5000]  # Increase from 2000 to 5000
        
        # Try to find substantial content
        paragraphs = text_after.split('\n\n')
        if len(paragraphs) < 2:
            paragraphs = text_after.split('\n')
        
        response_parts = []
        for paragraph in paragraphs[:50]:  # Increase to 50 paragraphs
            paragraph = paragraph.strip()
            if (len(paragraph) > 10 and 
                paragraph not in ['How can Grok help?', 'DeepSearch', 'Think', 'Send', 'Upload']):
                response_parts.append(paragraph)
        
        if response_parts:
            fallback_response = '\n\n'.join(response_parts)
            print(f"📋 Fallback extraction: {len(response_parts)} paragraphs, {len(fallback_response)} characters")
            return fallback_response
    
    return None

print("🤖 GROK CHAT INTERFACE")
print("=" * 40)
print(f"❓ Question: {question}")
print("=" * 40)

try:
    # Enable Runtime and DOM
    send_cdp_command("Runtime.enable", {}, 1)
    send_cdp_command("DOM.enable", {}, 2)
    
    # Send the message
    if send_message_to_grok(question):
        # Wait for and extract response
        response = wait_for_response(120)
        
        if response:
            print(f"\n✅ SUCCESS! Grok responded: '{response}'")
        else:
            print("\n❌ No response received within timeout period")
            
            # Try to extract any recent content for debugging
            print("\n🔍 Checking for any recent content...")
            current_text = get_page_text()
            if question in current_text:
                question_pos = current_text.rfind(question)
                recent_text = current_text[question_pos:question_pos + 500]
                print(f"📝 Recent content around question:\n{recent_text}")
    else:
        print("❌ Failed to send message")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    ws.close()
    print("\n✅ Session completed!")
