import websocket
import json
import sys
import time
import re
import pychrome

# Check if question was provided as argument
if len(sys.argv) < 2:
    print("❌ Usage: python grok_cdp_pychrome_hybrid_generator.py \"Your question here\"")
    print("📝 Example: python grok_cdp_pychrome_hybrid_generator.py \"What is the weather like today?\"")
    sys.exit(1)

question = sys.argv[1]

# WebSocket URL and tab ID from the provided JSON
ws_url = "ws://localhost:9222/devtools/page/E8CF09D134FAEB497BC8E90CBB705C86"
tab_id = "E8CF09D134FAEB497BC8E90CBB705C86"

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

def connect_pychrome():
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

# Initialize connections
ws = connect_websocket(ws_url)
browser, pychrome_tab = connect_pychrome()

def send_cdp_command(method, params, command_id):
    """Send CDP command via WebSocket"""
    command = {"id": command_id, "method": method, "params": params}
    ws.send(json.dumps(command))
    
    while True:
        response = json.loads(ws.recv())
        if 'id' in response and response['id'] == command_id:
            return response
        elif 'method' in response:
            continue

def send_message_to_grok_cdp(message):
    """Send a message to Grok via CDP (from original g_ask_grok.py)"""
    print(f"📤 Sending message via CDP: '{message}'")
    
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
    
    print("✅ Message sent via CDP!")
    return True

def stream_grok_chunks(timeout=180):
    """Generator function that yields chunks as they arrive from Grok"""
    print(f"⏳ Starting chunk streaming via PyChrome (timeout: {timeout}s)...")
    
    # Wait a bit for the message to be processed
    time.sleep(3)
    
    # Get initial page content to establish baseline
    content_expr = "document.body.innerText"
    result = pychrome_tab.call_method("Runtime.evaluate", expression=content_expr, returnByValue=True)
    
    if 'result' not in result or 'value' not in result['result']:
        raise ValueError(f"Failed to get initial page content. Result: {result}")
    
    initial_content = result['result']['value']
    initial_content_length = len(initial_content)
    print(f"📊 Initial content length: {initial_content_length}")
    
    start_time = time.time()
    last_length = initial_content_length
    last_content = initial_content
    stable_count = 0
    reasoning_detected = False
    search_detected = False
    
    print("🔄 Starting chunk generation...")
    
    while time.time() - start_time < timeout:
        time.sleep(3)  # Check every 3 seconds
        
        # Get current content
        result = pychrome_tab.call_method("Runtime.evaluate", expression=content_expr, returnByValue=True)
        current_content = result.get('result', {}).get('value', '')
        current_length = len(current_content)
        
        # Check for reasoning/thinking indicators
        if any(indicator in current_content.lower() for indicator in 
               ['searching for', 'let me search', 'thinking', 'reasoning', 'quick answer']):
            if not reasoning_detected:
                print("🧠 Detected Grok reasoning/searching phase...")
                reasoning_detected = True
            if 'searching for' in current_content.lower():
                search_detected = True
                print("🔍 Grok is searching for information...")
        
        # Check if content has grown
        if current_length > last_length + 15:
            stable_count = 0
            print(f"📈 Content growing: {current_length} chars (+{current_length - initial_content_length} from start)")
            
            # Yield the new chunk
            if len(current_content) > len(last_content):
                new_chunk = current_content[len(last_content):]
                chunk_info = {
                    'chunk': new_chunk,
                    'chunk_size': len(new_chunk),
                    'total_size': current_length,
                    'growth_from_start': current_length - initial_content_length,
                    'timestamp': time.time() - start_time
                }
                yield chunk_info
            
            last_length = current_length
            last_content = current_content
            continue
        else:
            stable_count += 1
            print(f"⏸️  Content stable for {stable_count * 3} seconds ({current_length} chars)")
        
        # Determine required stability based on reasoning detection
        required_stable_checks = 10 if reasoning_detected else 6
        
        # Check completion conditions
        if stable_count >= required_stable_checks:
            print(f"✅ Content stable for {stable_count * 3} seconds, streaming complete")
            break
        
        # Special handling for search responses
        if search_detected and current_length < initial_content_length + 1000:
            print("🔍 Search detected but response incomplete, continuing...")
            stable_count = 0
            continue
        
        # Early completion for substantial responses
        if (current_length > initial_content_length + 500 and 
            stable_count >= 5 and 
            time.time() - start_time > 20):
            print(f"✅ Substantial content stable for {stable_count * 3}s, completing...")
            break
    
    # Final reasoning wait if detected
    if reasoning_detected:
        print("🧠 Final reasoning wait...")
        time.sleep(10)
        result = pychrome_tab.call_method("Runtime.evaluate", expression=content_expr, returnByValue=True)
        final_content = result.get('result', {}).get('value', '')
        
        # Yield final chunk if there's new content
        if len(final_content) > len(last_content):
            final_chunk = final_content[len(last_content):]
            chunk_info = {
                'chunk': final_chunk,
                'chunk_size': len(final_chunk),
                'total_size': len(final_content),
                'growth_from_start': len(final_content) - initial_content_length,
                'timestamp': time.time() - start_time,
                'is_final': True
            }
            yield chunk_info

def get_full_response():
    """Get the complete response after streaming is done"""
    content_expr = "document.body.innerText"
    result = pychrome_tab.call_method("Runtime.evaluate", expression=content_expr, returnByValue=True)
    
    if 'result' not in result or 'value' not in result['result']:
        return None
    
    full_content = result['result']['value']
    
    # Extract meaningful response
    if question in full_content:
        question_pos = full_content.rfind(question)
        text_after_question = full_content[question_pos + len(question):]
        
        lines = text_after_question.split('\n')
        meaningful_lines = []
        
        for line in lines[:200]:
            line = line.strip()
            if (len(line) > 5 and 
                not line in ['How can Grok help?', 'DeepSearch', 'Think', 'Send', 'Upload', 'Grok 3', 'Upgrade to SuperGrok', 'Think Harder'] and
                not re.match(r'^\d+[smh]$', line) and
                not line.isdigit() and
                not line in ['Copy', 'Wrap', 'Collapse']):
                meaningful_lines.append(line)
        
        if meaningful_lines:
            return '\n\n'.join(meaningful_lines)
    
    return full_content

print("🤖 GROK CDP + PYCHROME HYBRID GENERATOR")
print("=" * 50)
print(f"❓ Question: {question}")
print("=" * 50)

try:
    # Enable CDP domains
    send_cdp_command("Runtime.enable", {}, 1)
    send_cdp_command("DOM.enable", {}, 2)
    
    # Send the message using CDP
    if send_message_to_grok_cdp(question):
        print("\n🔄 Starting chunk streaming...")
        print("=" * 50)
        
        # Stream chunks using generator
        total_chunks = 0
        total_chars = 0
        
        for chunk_info in stream_grok_chunks(180):
            total_chunks += 1
            total_chars += chunk_info['chunk_size']
            
            print(f"📦 Chunk #{total_chunks} ({chunk_info['chunk_size']} chars, {chunk_info['timestamp']:.1f}s):")
            print("─" * 60)
            print(chunk_info['chunk'][:300] + ("..." if len(chunk_info['chunk']) > 300 else ""))
            print("─" * 60)
            
            if chunk_info.get('is_final'):
                print("🏁 Final chunk received!")
        
        print(f"\n📊 Streaming complete: {total_chunks} chunks, {total_chars} characters")
        
        # Get full response
        print("\n🔍 Extracting full response...")
        full_response = get_full_response()
        
        if full_response:
            print("\n🎉 SUCCESS! Full response extracted!")
            print("=" * 50)
            print("🤖 COMPLETE GROK RESPONSE:")
            print("=" * 50)
            print(full_response)
            print("=" * 50)
        else:
            print("\n❌ Failed to extract full response")
    else:
        print("❌ Failed to send message via CDP")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Clean up connections without closing the tab
    try:
        ws.close()
        print("✅ CDP WebSocket closed")
    except:
        pass
    
    try:
        pychrome_tab.stop()
        print("✅ PyChrome connection stopped (tab remains open)")
    except:
        pass
    
    print("\n✅ Hybrid generator test completed!")
