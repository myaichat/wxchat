import websocket
import json
import sys
import time
import re


# WebSocket URL from the provided JSON
ws_url = "ws://localhost:9222/devtools/page/E8CF09D134FAEB497BC8E90CBB705C86"

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

def send_message_with_streaming(question, timeout=120):
    """Stream Grok's response in real-time as it appears"""
    print(f"⏳ Starting to stream Grok's response (timeout: {timeout}s)...")
    
    # First, send the message to Grok
    if not send_message_to_grok(question):
        print("❌ Failed to send message to Grok")
        return
    
    # Wait a moment for the message to be processed
    time.sleep(2)
    
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
                        
                    # Skip known UI elements
                    if paragraph in ['How can Grok help?', 'DeepSearch', 'Think', 'Send', 'Upload', 'Grok 3', 'Upgrade to SuperGrok', 'markdown', 'Collapse', 'Wrap', 'Copy']:
                        if found_start:
                            print(f"🛑 Found end marker: '{paragraph}', stopping stream")
                            break
                        continue
                    
                    # Skip time indicators and pure numbers
                    if re.match(r'^\d+\.?\d*[smh]$', paragraph) or paragraph.isdigit():
                        continue
                    
                    # Include content
                    if len(paragraph) > 5:
                        if not found_start:
                            print(f"🎯 Response started: '{paragraph[:50]}...'")
                            response_started = True
                        found_start = True
                        current_response_parts.append(paragraph)
                
                # Join current response
                current_response = '\n\n'.join(current_response_parts)
                
                # Yield only new content (delta)
                if current_response and current_response != last_yielded_content:
                    if last_yielded_content:
                        # Find the new part
                        if current_response.startswith(last_yielded_content):
                            new_content = current_response[len(last_yielded_content):].strip()
                            if new_content:
                                print(f"📤 Streaming new content: '{new_content[:100]}...'")
                                yield new_content
                        else:
                            # Content changed significantly - find what's actually new
                            # This can happen when Grok reformats or restructures the response
                            print(f"📤 Content restructured, finding delta...")
                            
                            # Try to find common prefix and yield only the new part
                            common_len = 0
                            min_len = min(len(last_yielded_content), len(current_response))
                            
                            # Find how much content is the same from the beginning
                            for i in range(min_len):
                                if last_yielded_content[i] == current_response[i]:
                                    common_len = i + 1
                                else:
                                    break
                            
                            # Yield only the new part after the common prefix
                            if len(current_response) > common_len:
                                new_content = current_response[common_len:].strip()
                                if new_content:
                                    print(f"📤 Streaming delta after restructure: '{new_content[:100]}...'")
                                    yield new_content
                    else:
                        # First content - yield the entire response for the first time
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

def main(question, timeout=120):
    """Main function to run the streaming Grok chat"""
    print("🤖 GROK STREAMING CHAT INTERFACE")
    print("=" * 40)
    print(f"❓ Question: {question}")
    print("=" * 40)
    
    try:
        # Enable Runtime and DOM
        send_cdp_command("Runtime.enable", {}, 1)
        send_cdp_command("DOM.enable", {}, 2)
        
        # Send the message
        if send_message_to_grok(question):
            print("\n🔄 Starting response stream...")
            print("=" * 40)
            
            # Stream the response
            full_response = ""
            for chunk in send_message_with_streaming(question,timeout):
                if chunk:
                    print(chunk, end='', flush=True)  # Print without newline for streaming effect
                    full_response += chunk
            
            print("\n" + "=" * 40)
            if full_response:
                print(f"✅ STREAMING COMPLETE! Total response length: {len(full_response)} characters")
            else:
                print("❌ No response received")
        else:
            print("❌ Failed to send message")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ws.close()
        print("\n✅ Session completed!")

# Generator function for use by other scripts
def ask_grok_streaming(question_text, timeout=120, ws_url_override=None):
    """
    Generator function that yields Grok response chunks in real-time.
    Can be imported and used by other scripts.
    
    Args:
        question_text (str): The question to ask Grok
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
        if send_message_to_grok(question):
            # Stream the response
            for chunk in send_message_with_streaming(question, timeout):
                if chunk:
                    yield chunk
        else:
            yield "❌ Failed to send message to Grok"
    
    except Exception as e:
        yield f"❌ Error: {e}"
    finally:
        if 'ws' in globals():
            ws.close()

if __name__ == "__main__":

    # Check if question was provided as argument
    if len(sys.argv) < 2:
        print("❌ Usage: python g_ask_grok_streaming.py \"Your question here\"")
        print("📝 Example: python g_ask_grok_streaming.py \"What is the weather like today?\"")
        sys.exit(1)

    question = sys.argv[1]

    main(question)
