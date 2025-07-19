import websocket
import json
import sys
import time
import re

# Check if question was provided as argument
if len(sys.argv) < 2:
    print("❌ Usage: python p_ask_perplexity.py \"Your question here\"")
    print("📝 Example: python p_ask_perplexity.py \"What is the weather like today?\"")
    sys.exit(1)

question = sys.argv[1]

# WebSocket URL from the provided JSON
ws_url = "ws://localhost:9222/devtools/page/29B3BE6316EBE92AEE30FACE6A319AF0"

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

def send_message_to_perplexity(message):
    """Send a message to Perplexity via the textarea or input field"""
    print(f"📤 Sending message: '{message}'")
    
    # Get document
    send_cdp_command("DOM.getDocument", {}, 1)
    
    # Try to find textarea first, then input field
    textarea_response = send_cdp_command(
        "DOM.querySelector",
        {"nodeId": 1, "selector": "textarea"},
        2
    )
    
    input_node_id = None
    if textarea_response.get('result', {}).get('nodeId'):
        input_node_id = textarea_response['result']['nodeId']
        print("📝 Found textarea element")
    else:
        # Try input field
        input_response = send_cdp_command(
            "DOM.querySelector",
            {"nodeId": 1, "selector": "input[type='text'], input[placeholder*='Ask'], input[placeholder*='search']"},
            3
        )
        
        if input_response.get('result', {}).get('nodeId'):
            input_node_id = input_response['result']['nodeId']
            print("📝 Found input element")
        else:
            # Try more generic selectors
            generic_response = send_cdp_command(
                "DOM.querySelector",
                {"nodeId": 1, "selector": "[contenteditable='true'], [role='textbox']"},
                4
            )
            
            if generic_response.get('result', {}).get('nodeId'):
                input_node_id = generic_response['result']['nodeId']
                print("📝 Found contenteditable element")
    
    if not input_node_id:
        print("❌ Could not find input field!")
        return False
    
    # Focus on input field
    send_cdp_command("DOM.focus", {"nodeId": input_node_id}, 5)
    
    # Clear existing text
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Control"}, 6)
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyDown", "key": "KeyA"}, 7)
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyUp", "key": "KeyA"}, 8)
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Control"}, 9)
    
    # Type the message
    command_id = 10
    for char in message:
        send_cdp_command("Input.dispatchKeyEvent", {"type": "char", "text": char}, command_id)
        command_id += 1
        time.sleep(0.02)
    
    # Press Enter to send
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter"}, command_id)
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter"}, command_id + 1)
    
    print("✅ Message sent!")
    return True

def wait_for_response(timeout=120):
    """Wait for Perplexity's response and extract it"""
    print(f"⏳ Waiting for Perplexity's response (timeout: {timeout}s)...")
    
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
                    
                    # Find the response content - RELAXED CRITERIA for Perplexity
                    response_parts = []
                    found_start = False
                    
                    # Perplexity-specific UI elements to skip
                    perplexity_ui_elements = [
                        'Ask anything...', 'Search', 'Pro', 'Sources', 'Related', 
                        'Follow-up', 'Share', 'Copy', 'Regenerate', 'Ask follow-up',
                        'View sources', 'Pro Search', 'Focus', 'All', 'Academic',
                        'Writing', 'Wolfram|Alpha', 'YouTube', 'Reddit', 'News'
                    ]
                    
                    for paragraph in paragraphs[:200]:  # Check up to 200 paragraphs
                        paragraph = paragraph.strip()
                        
                        # Skip empty content
                        if not paragraph:
                            continue
                            
                        # Skip known Perplexity UI elements
                        if paragraph in perplexity_ui_elements:
                            if found_start:
                                print(f"🛑 Found end marker: '{paragraph}', stopping extraction")
                                break
                            continue
                        
                        # Skip time indicators, pure numbers, and very short content
                        if (re.match(r'^\d+\.?\d*[smh]$', paragraph) or 
                            paragraph.isdigit() or 
                            len(paragraph) < 3):
                            continue
                        
                        # Skip source indicators like "[1]", "[2]", etc.
                        if re.match(r'^\[\d+\]$', paragraph):
                            continue
                        
                        # Include substantial content
                        if len(paragraph) > 5:  # Lower threshold for Perplexity
                            if not found_start:
                                print(f"🎯 Found response start: '{paragraph[:50]}...'")
                            found_start = True
                            response_parts.append(paragraph)
                    
                    if response_parts:
                        # Join with appropriate spacing
                        full_response = '\n\n'.join(response_parts)
                        
                        print(f"\n🎉 FOUND COMPLETE PERPLEXITY RESPONSE!")
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
        text_after = current_text[question_pos:question_pos + 5000]
        
        # Try to find substantial content
        paragraphs = text_after.split('\n\n')
        if len(paragraphs) < 2:
            paragraphs = text_after.split('\n')
        
        response_parts = []
        perplexity_ui_elements = [
            'Ask anything...', 'Search', 'Pro', 'Sources', 'Related', 
            'Follow-up', 'Share', 'Copy', 'Regenerate'
        ]
        
        for paragraph in paragraphs[:50]:
            paragraph = paragraph.strip()
            if (len(paragraph) > 10 and 
                paragraph not in perplexity_ui_elements and
                not re.match(r'^\[\d+\]$', paragraph)):
                response_parts.append(paragraph)
        
        if response_parts:
            fallback_response = '\n\n'.join(response_parts)
            print(f"📋 Fallback extraction: {len(response_parts)} paragraphs, {len(fallback_response)} characters")
            return fallback_response
    
    return None

print("🔍 PERPLEXITY CHAT INTERFACE")
print("=" * 40)
print(f"❓ Question: {question}")
print("=" * 40)

try:
    # Enable Runtime and DOM
    send_cdp_command("Runtime.enable", {}, 1)
    send_cdp_command("DOM.enable", {}, 2)
    
    # Send the message
    if send_message_to_perplexity(question):
        # Wait for and extract response
        response = wait_for_response(120)
        
        if response:
            print(f"\n✅ SUCCESS! Perplexity Response Received!")
            print("=" * 60)
            print(response)
            print("=" * 60)
            print(f"📊 Response length: {len(response)} characters")
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
