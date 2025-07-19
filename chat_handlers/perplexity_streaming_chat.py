import websocket
import json
import sys
import time
import re


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

def stream_perplexity_response(timeout=120):
    """Stream Perplexity's response in real-time as it appears"""
    print(f"⏳ Starting to stream Perplexity's response (timeout: {timeout}s)...")
    
    # Get initial page content
    initial_text = get_page_text()
    initial_length = len(initial_text)
    
    # Track what we've already yielded
    last_yielded_content = ""
    last_content_length = initial_length
    
    start_time = time.time()
    stable_count = 0
    max_stable_time = 8  # Reduced from 12 to 8 seconds for faster streaming
    response_started = False
    
    print("🔄 Monitoring for new content...")
    
    # Perplexity-specific UI elements to skip
    perplexity_ui_elements = [
        'Ask anything...', 'Search', 'Pro', 'Sources', 'Related', 
        'Follow-up', 'Share', 'Copy', 'Regenerate', 'Ask follow-up',
        'View sources', 'Pro Search', 'Focus', 'All', 'Academic',
        'Writing', 'Wolfram|Alpha', 'YouTube', 'Reddit', 'News'
    ]
    
    while time.time() - start_time < timeout:
        time.sleep(1)  # Check every 1 second for more responsive streaming
        
        current_text = get_page_text()
        current_length = len(current_text)
        
        # Check if content has grown
        if current_length > last_content_length + 50:  # Lower threshold for more responsive streaming
            print(f"📈 Content increased: {last_content_length} → {current_length}")
            
            # Extract new content since our question
            if question in current_text:
                question_pos = current_text.rfind(question)
                text_after_question = current_text[question_pos + len(question):]
                
                # Process the content to find response parts
                paragraphs = text_after_question.split('\n\n')
                if len(paragraphs) < 2:
                    paragraphs = text_after_question.split('\n')
                
                # Build current response content
                current_response_parts = []
                found_start = False
                
                for paragraph in paragraphs[:100]:
                    paragraph = paragraph.strip()
                    
                    # Skip empty content
                    if not paragraph:
                        continue
                        
                    # Skip known Perplexity UI elements
                    if paragraph in perplexity_ui_elements:
                        if found_start:
                            print(f"🛑 Found end marker: '{paragraph}', stopping stream")
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
                            print(f"🎯 Response started: '{paragraph[:50]}...'")
                            response_started = True
                        found_start = True
                        current_response_parts.append(paragraph)
                
                # Join current response
                current_response = '\n\n'.join(current_response_parts)
                
                # Yield only new content
                if current_response and current_response != last_yielded_content:
                    if last_yielded_content:
                        # Find the new part
                        if current_response.startswith(last_yielded_content):
                            new_content = current_response[len(last_yielded_content):].strip()
                            if new_content:
                                print(f"📤 Streaming new content: '{new_content[:100]}...'")
                                yield new_content
                        else:
                            # Content changed significantly, try to find common parts
                            # Split both into lines and find where they diverge
                            old_lines = last_yielded_content.split('\n') if last_yielded_content else []
                            new_lines = current_response.split('\n')
                            
                            # Find the longest common prefix
                            common_length = 0
                            for i, (old_line, new_line) in enumerate(zip(old_lines, new_lines)):
                                if old_line == new_line:
                                    common_length = i + 1
                                else:
                                    break
                            
                            # Get only the new lines
                            if common_length < len(new_lines):
                                new_content = '\n'.join(new_lines[common_length:]).strip()
                                if new_content:
                                    print(f"📤 Streaming new content: '{new_content[:100]}...'")
                                    yield new_content
                    else:
                        # First content
                        print(f"📤 Streaming initial content: '{current_response[:100]}...'")
                        yield current_response
                    
                    last_yielded_content = current_response
                    stable_count = 0  # Reset stability counter when new content appears
                else:
                    stable_count += 1
                    if response_started:
                        print(f"⏸️  Content stable for {stable_count} seconds")
            
            last_content_length = current_length
        else:
            # No significant growth
            if response_started:
                stable_count += 1
                if stable_count >= max_stable_time:
                    print(f"✅ Response appears complete (stable for {stable_count} seconds)")
                    break
    
    if not response_started:
        print("⚠️  No response detected within timeout period")
    else:
        print("🏁 Streaming completed")

def main(question):
    """Main function to run the streaming Perplexity chat"""
    print("🔍 PERPLEXITY STREAMING CHAT INTERFACE")
    print("=" * 40)
    print(f"❓ Question: {question}")
    print("=" * 40)
    
    try:
        print("\n🔄 Starting response stream...")
        print("=" * 40)
        
        # Use the send_message_with_streaming function
        full_response = ""
        chunk_count = 0
        start_time = time.time()
        
        for chunk in send_message_with_streaming(question, timeout=120):
            if chunk:
                chunk_count += 1
                elapsed = time.time() - start_time
                timestamp = time.strftime("%H:%M:%S", time.localtime())
                
                # Check if it's an error message
                if chunk.startswith("❌"):
                    print(f"\n[{timestamp}] [{elapsed:.1f}s] ERROR CHUNK #{chunk_count}: {chunk}")
                    break
                else:
                    print(f"\n[{timestamp}] [{elapsed:.1f}s] YIELD CHUNK #{chunk_count} ({len(chunk)} chars):")
                    print("─" * 60)
                    print(chunk)
                    print("─" * 60)
                    full_response += chunk
        
        print("\n" + "=" * 40)
        if full_response:
            total_elapsed = time.time() - start_time
            print(f"✅ STREAMING COMPLETE! Total chunks: {chunk_count}, Total response length: {len(full_response)} characters, Total time: {total_elapsed:.1f}s")
        else:
            print("❌ No response received")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Session completed!")

# Generator function for use by other scripts
def send_message_with_streaming(question_text, timeout=120,ws_url_override=None):
    """
    Generator function that yields Perplexity response chunks in real-time.
    Can be imported and used by other scripts.
    
    Args:
        question_text (str): The question to ask Perplexity
        ws_url_override (str, optional): Override WebSocket URL
    
    Yields:
        str: Response chunks as they become available
    """
    global ws, question, ws_url
    
    if ws_url_override:
        ws_url = ws_url_override
    
    question = question_text
    
    try:
        # Connect to WebSocket
        ws = connect_websocket(ws_url)
        
        # Enable Runtime and DOM
        send_cdp_command("Runtime.enable", {}, 1)
        send_cdp_command("DOM.enable", {}, 2)
        
        # Send the message
        if send_message_to_perplexity(question):
            # Stream the response
            for chunk in stream_perplexity_response(timeout):
                if chunk:
                    yield chunk
        else:
            yield "❌ Failed to send message to Perplexity"
    
    except Exception as e:
        yield f"❌ Error: {e}"
    finally:
        if 'ws' in globals():
            ws.close()

if __name__ == "__main__":

    # Check if question was provided as argument
    if len(sys.argv) < 2:
        print("❌ Usage: python p_ask_perplexity_streaming.py \"Your question here\"")
        print("📝 Example: python p_ask_perplexity_streaming.py \"What is the weather like today?\"")
        sys.exit(1)

    question = sys.argv[1]

    main(question)
