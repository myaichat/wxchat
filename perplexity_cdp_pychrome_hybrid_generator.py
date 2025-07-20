import websocket
import json
import sys
import time
import re
import pychrome
from pprint import pprint

# Default WebSocket URL and tab ID from the provided JSON
DEFAULT_WS_URL = "ws://localhost:9222/devtools/page/F583A4254DC132512B2654E4517790F0"
DEFAULT_TAB_ID = "F583A4254DC132512B2654E4517790F0"

def connect_websocket(ws_url):
    """Connect to CDP WebSocket for sending messages"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            ws = websocket.create_connection(ws_url)
            print("✅ CDP WebSocket connected")
            return ws
        except Exception as e:
            print(f"❌ CDP WebSocket connection failed (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(2)
    raise Exception("Failed to connect to CDP WebSocket after retries")

def connect_pychrome(tab_id=DEFAULT_TAB_ID):
    """Connect to browser using pychrome for reading responses"""
    try:
        browser = pychrome.Browser(url="http://localhost:9222")
        tabs = browser.list_tab()
        tab = None
        for t in tabs:
            if t.id == tab_id:
                tab = t
                break
        
        if tab is None:
            raise ValueError("Tab with specified ID not found.")
        
        tab.start()
        tab.call_method("Runtime.enable")
        print("✅ PyChrome connected")
        return browser, tab
    except Exception as e:
        print(f"❌ PyChrome connection failed: {e}")
        raise

# Global connection variables (will be initialized when needed)
_ws = None
_browser = None
_pychrome_tab = None

def _ensure_connections(ws_url=DEFAULT_WS_URL, tab_id=DEFAULT_TAB_ID):
    """Ensure connections are established"""
    global _ws, _browser, _pychrome_tab
    
    if _ws is None:
        _ws = connect_websocket(ws_url)
    
    if _browser is None or _pychrome_tab is None:
        _browser, _pychrome_tab = connect_pychrome(tab_id)

def send_cdp_command(method, params, command_id, ws_url=DEFAULT_WS_URL, tab_id=DEFAULT_TAB_ID):
    """Send CDP command via WebSocket"""
    _ensure_connections(ws_url, tab_id)
    
    command = {"id": command_id, "method": method, "params": params}
    _ws.send(json.dumps(command))
    
    while True:
        response = json.loads(_ws.recv())
        if 'id' in response and response['id'] == command_id:
            return response
        elif 'method' in response:
            continue

def send_message_to_perplexity_cdp(message, timeout, ws_url=DEFAULT_WS_URL, tab_id=DEFAULT_TAB_ID):
    """Send a message to Perplexity via CDP"""
    _ensure_connections(ws_url, tab_id)
    
    print(f"📤 Sending message via CDP: '{message}'")
    
    # Get document
    send_cdp_command("DOM.getDocument", {}, 1, ws_url, tab_id)
    
    # Try multiple selectors for Perplexity's input field
    selectors = [
        "#ask-input",  # Primary Perplexity input ID
        "textarea",
        "[role='textbox']",
        "[contenteditable='true']",
        "input[type='text']",
        "input[placeholder*='Ask']",
        "input[placeholder*='search']"
    ]
    
    input_node_id = None
    for selector in selectors:
        input_response = send_cdp_command(
            "DOM.querySelector",
            {"nodeId": 1, "selector": selector},
            2, ws_url, tab_id
        )
        
        if input_response.get('result', {}).get('nodeId'):
            input_node_id = input_response['result']['nodeId']
            print(f"📝 Found input element with selector: {selector}")
            break
    
    if not input_node_id:
        print("❌ Could not find input field!")
        return False
    
    # Focus on input field
    send_cdp_command("DOM.focus", {"nodeId": input_node_id}, 3, ws_url, tab_id)
    
    # Clear existing text
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Control"}, 4, ws_url, tab_id)
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyDown", "key": "KeyA"}, 5, ws_url, tab_id)
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyUp", "key": "KeyA"}, 6, ws_url, tab_id)
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Control"}, 7, ws_url, tab_id)
    
    # Type the message
    command_id = 8
    for char in message:
        send_cdp_command("Input.dispatchKeyEvent", {"type": "char", "text": char}, command_id, ws_url, tab_id)
        command_id += 1
        time.sleep(0.02)
    
    # Press Enter to send
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter"}, command_id, ws_url, tab_id)
    send_cdp_command("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter"}, command_id + 1, ws_url, tab_id)
    
    print("✅ Message sent via CDP!")
    return True

def send_message_with_streaming(question, timeout=180, ws_url=DEFAULT_WS_URL, tab_id=DEFAULT_TAB_ID):
    """Generator function that yields full response first, then incremental chunks"""
    _ensure_connections(ws_url, tab_id)
    
    print(f"⏳ Starting chunk streaming via PyChrome (timeout: {timeout}s)...")
    
    # Enable CDP domains
    send_cdp_command("Runtime.enable", {}, 1, ws_url, tab_id)
    send_cdp_command("DOM.enable", {}, 2, ws_url, tab_id)
    
    # Send the message using CDP
    if not send_message_to_perplexity_cdp(question, timeout, ws_url, tab_id):
        print("❌ Failed to send message via CDP")
        return
    
    print("\n🔄 Starting chunk streaming...")
    print("=" * 50)
    
    # Wait a bit for the message to be processed and response to start
    time.sleep(3)
    
    start_time = time.time()
    previous_len = 0
    first_chunk = True
    stable_count = 0
    reasoning_detected = False
    last_chunk_time = time.time()
    
    print("🔄 Starting chunk generation - full response first, then increments...")
    
    while time.time() - start_time < timeout:
        time.sleep(0.5)  # Check every 0.5 seconds for better responsiveness
        
        # Get current full response
        current_response = get_full_response(question) or ""
        current_length = len(current_response)
        
        # Check for reasoning/thinking indicators specific to Perplexity
        if any(indicator in current_response.lower() for indicator in 
               ['searching', 'let me search', 'thinking', 'analyzing', 'looking up', 'finding information']):
            if not reasoning_detected:
                print("🧠 Detected Perplexity reasoning/searching phase...")
                reasoning_detected = True
        
        # If this is the first chunk and we have content, yield full response
        if first_chunk and current_length > 0:
            print(f"📦 First chunk: {current_length} chars (full response)")
            chunk_info = {
                'chunk': current_response,
                'chunk_size': current_length,
                'total_size': current_length,
                'timestamp': time.time() - start_time,
                'is_first': True,
                'is_filtered_out': len(current_response.strip()) == 0
            }
            yield chunk_info
            previous_len = current_length
            first_chunk = False
            last_chunk_time = time.time()
            stable_count = 0
            continue
        
        # If response has grown, yield incremental content
        if current_length > previous_len:
            increment = current_response[previous_len:]
            print(f"📦 Increment: {len(increment)} chars (total: {current_length})")
            chunk_info = {
                'chunk': increment,
                'chunk_size': len(increment),
                'total_size': current_length,
                'timestamp': time.time() - start_time,
                'is_filtered_out': len(increment.strip()) == 0
            }
            yield chunk_info
            previous_len = current_length
            last_chunk_time = time.time()
            stable_count = 0
            continue
        else:
            # No growth, check stability
            stable_count += 1
            elapsed_stable = stable_count * 0.5
            print(f"⏸️  Response stable for {elapsed_stable:.1f} seconds ({current_length} chars)")
        
        # Determine required stability based on reasoning detection and content size
        if reasoning_detected:
            required_stable_time = 30.0  # 30 seconds for reasoning responses
        elif current_length > 1000:
            required_stable_time = 15.0   # 15 seconds for substantial responses
        else:
            required_stable_time = 8.0    # 8 seconds for shorter responses
        
        # Check completion conditions
        elapsed_stable = stable_count * 0.5
        if elapsed_stable >= required_stable_time:
            print(f"✅ Content stable for {elapsed_stable:.1f} seconds, streaming complete")
            break
        
        # Timeout check for very long responses
        if time.time() - last_chunk_time > 60:  # No new chunks for 60 seconds
            print("⏰ No new content for 60 seconds, assuming complete")
            break
    
    # Final chunk marker
    chunk_info = {
        'chunk': '',
        'chunk_size': 0,
        'total_size': previous_len,
        'timestamp': time.time() - start_time,
        'is_final': True,
        'is_filtered_out': False
    }
    yield chunk_info

def filter_chunk_content(chunk):
    """Filter chunk content to remove Perplexity UI elements"""
    lines = chunk.split('\n')
    filtered_lines = []
    
    # Perplexity-specific UI elements to filter out
    perplexity_ui_elements = [
        'Ask anything...', 'Search', 'Pro', 'Sources', 'Related', 
        'Follow-up', 'Share', 'Copy', 'Regenerate', 'Ask follow-up',
        'View sources', 'Pro Search', 'Focus', 'All', 'Academic',
        'Writing', 'Wolfram|Alpha', 'YouTube', 'Reddit', 'News'
    ]
    
    for line in lines:
        line = line.strip()
        if (len(line) > 0 and 
            not line in perplexity_ui_elements and
            not re.match(r'^\d+[smh]$', line) and
            not line.isdigit() and
            not re.match(r'^\[\d+\]$', line) and  # Filter source indicators like [1], [2]
            not line in ['Copy', 'Wrap', 'Collapse']):
            filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)

def get_full_response(question):
    """Get the complete response after streaming is done"""
    global _pychrome_tab
    
    if _pychrome_tab is None:
        return None
        
    content_expr = "document.body.innerText"
    result = _pychrome_tab.call_method("Runtime.evaluate", expression=content_expr, returnByValue=True)
    
    if 'result' not in result or 'value' not in result['result']:
        return None
    
    full_content = result['result']['value']
    
    # Extract meaningful response
    if question in full_content:
        question_pos = full_content.rfind(question)
        text_after_question = full_content[question_pos + len(question):]
        
        lines = text_after_question.split('\n')
        meaningful_lines = []
        
        # Perplexity-specific UI elements to skip
        perplexity_ui_elements = [
            'Ask anything...', 'Search', 'Pro', 'Sources', 'Related', 
            'Follow-up', 'Share', 'Copy', 'Regenerate', 'Ask follow-up',
            'View sources', 'Pro Search', 'Focus', 'All', 'Academic',
            'Writing', 'Wolfram|Alpha', 'YouTube', 'Reddit', 'News'
        ]
        
        for line in lines:
            line = line.strip()
            if (len(line) > 5 and 
                not line in perplexity_ui_elements and
                not re.match(r'^\d+\.?\d*[smh]$', line) and
                not line.isdigit() and
                not re.match(r'^\[\d+\]$', line) and  # Skip source indicators
                not line in ['Copy', 'Wrap', 'Collapse']):
                meaningful_lines.append(line)
        
        if meaningful_lines:
            return '\n\n'.join(meaningful_lines)
    
    return full_content

def cleanup_connections():
    """Clean up connections without closing the tab"""
    global _ws, _browser, _pychrome_tab
    
    try:
        if _ws:
            _ws.close()
            print("✅ CDP WebSocket closed")
    except:
        pass
    
    try:
        if _pychrome_tab:
            _pychrome_tab.stop()
            print("✅ PyChrome connection stopped (tab remains open)")
    except:
        pass
    
    # Reset global variables
    _ws = None
    _browser = None
    _pychrome_tab = None

def main():
    """Main function to run the Perplexity CDP + PyChrome hybrid generator"""
    # Check if question was provided as argument
    if len(sys.argv) < 2:
        print("❌ Usage: python perplexity_cdp_pychrome_hybrid_generator.py \"Your question here\"")
        print("📝 Example: python perplexity_cdp_pychrome_hybrid_generator.py \"What is the weather like today?\"")
        sys.exit(1)

    question = sys.argv[1]
    
    print("🔍 PERPLEXITY CDP + PYCHROME HYBRID GENERATOR")
    print("=" * 50)
    print(f"❓ Question: {question}")
    print("=" * 50)

    try:
        # Stream chunks using generator
        total_chunks = 0
        total_chars = 0
        for chunk_info in send_message_with_streaming(question, 180):
            total_chunks += 1
            total_chars += chunk_info['chunk_size']
            
            chunk_type = "FIRST" if chunk_info.get('is_first') else "FINAL" if chunk_info.get('is_final') else "INCREMENTAL"
            filtered_out = " [FILTERED OUT]" if chunk_info.get('is_filtered_out') else ""
            print(f"📦 Chunk #{total_chunks} [{chunk_type}]{filtered_out} ({chunk_info['chunk_size']} chars, {chunk_info['timestamp']:.1f}s):")
            print("─" * 60)
            
            # Show chunk content
            if chunk_info['chunk_size'] > 0:
                if chunk_info.get('is_first'):
                    # Show full content for first chunk
                    print(chunk_info['chunk'])
                else:
                    # Truncate incremental chunks for readability
                    content_to_show = chunk_info['chunk'][:500] + ("..." if len(chunk_info['chunk']) > 500 else "")
                    print(content_to_show)
            print("─" * 60)
            
            if chunk_info.get('is_final'):
                print("🏁 Final chunk received!")
        
        print(f"\n📊 Streaming complete: {total_chunks} chunks, {total_chars} characters")
        
        # Get full response
        print("\n🔍 Extracting full response...")
        full_response = get_full_response(question)
        
        if 0 and full_response:
            print("\n🎉 SUCCESS! Full response extracted!")
            print("=" * 50)
            print("🔍 COMPLETE PERPLEXITY RESPONSE:")
            print("=" * 50)
            print(full_response)
            print("=" * 50)
        else:
            print("\n❌ Failed to extract full response")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup_connections()
        print("\n✅ Hybrid generator test completed!")


if __name__ == "__main__":
    main()
