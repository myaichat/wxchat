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

def stream_grok_chunks_with_baseline(baseline_response, timeout=180):
    """Generator function that yields chunks as they arrive from Grok"""
    print(f"⏳ Starting chunk streaming via PyChrome (timeout: {timeout}s)...")
    
    baseline_length = len(baseline_response)
    print(f"📊 Using provided baseline length: {baseline_length}")
    
    # Wait a bit for the message to be processed and response to start
    time.sleep(3)
    
    # Get initial response after waiting - this should capture the first chunk
    previous_response = get_full_response() or ""
    previous_length = len(previous_response)
    print(f"📊 Initial response length after wait: {previous_length}")
    
    # If there's already content beyond baseline, yield it as the first chunk
    if previous_length > baseline_length:
        first_chunk = previous_response[baseline_length:]
        print(f"📦 Found first chunk immediately: {len(first_chunk)} chars")
        
        chunk_info = {
            'chunk': first_chunk,
            'raw_chunk': first_chunk,
            'chunk_size': len(first_chunk),
            'raw_size': len(first_chunk),
            'total_size': previous_length,
            'growth_from_start': previous_length - baseline_length,
            'timestamp': 3.0,  # Approximate time
            'is_first': True,
            'is_filtered_out': len(first_chunk.strip()) == 0
        }
        yield chunk_info
    
    start_time = time.time()
    stable_count = 0
    reasoning_detected = False
    last_chunk_time = time.time()
    
    print("🔄 Starting chunk generation using full response comparison...")
    
    while time.time() - start_time < timeout:
        time.sleep(0.5)  # Check every 0.5 seconds for better responsiveness
        
        # Get current full response
        current_response = get_full_response() or ""
        current_length = len(current_response)
        
        # Check for reasoning/thinking indicators in raw content
        content_expr = "document.body.innerText"
        result = pychrome_tab.call_method("Runtime.evaluate", expression=content_expr, returnByValue=True)
        raw_content = result.get('result', {}).get('value', '')
        
        if any(indicator in raw_content.lower() for indicator in 
               ['searching for', 'let me search', 'thinking', 'reasoning', 'quick answer']):
            if not reasoning_detected:
                print("🧠 Detected Grok reasoning/searching phase...")
                reasoning_detected = True
        
        # Check if response has grown
        if current_length > previous_length:
            stable_count = 0
            last_chunk_time = time.time()
            growth = current_length - previous_length
            print(f"📈 Response growing: {current_length} chars (+{growth} new)")
            
            # Get the new chunk by comparing full responses
            new_chunk = current_response[previous_length:]
            
            chunk_info = {
                'chunk': new_chunk,
                'raw_chunk': new_chunk,
                'chunk_size': len(new_chunk),
                'raw_size': len(new_chunk),
                'total_size': current_length,
                'growth_from_start': current_length - baseline_length,
                'timestamp': time.time() - start_time,
                'is_filtered_out': len(new_chunk.strip()) == 0
            }
            yield chunk_info
            
            # Update tracking
            previous_response = current_response
            previous_length = current_length
            continue
        else:
            stable_count += 1
            elapsed_stable = stable_count * 0.5
            print(f"⏸️  Response stable for {elapsed_stable:.1f} seconds ({current_length} chars)")
        
        # Determine required stability based on reasoning detection and content size
        if reasoning_detected:
            required_stable_time = 15.0  # 15 seconds for reasoning responses
        elif current_length > 1000:
            required_stable_time = 8.0   # 8 seconds for substantial responses
        else:
            required_stable_time = 5.0   # 5 seconds for shorter responses
        
        # Check completion conditions
        elapsed_stable = stable_count * 0.5
        if elapsed_stable >= required_stable_time:
            print(f"✅ Content stable for {elapsed_stable:.1f} seconds, streaming complete")
            break
        
        # Timeout check for very long responses
        if time.time() - last_chunk_time > 30:  # No new chunks for 30 seconds
            print("⏰ No new content for 30 seconds, assuming complete")
            break
    
    # Final reasoning wait if detected and we haven't been stable for long
    if reasoning_detected and elapsed_stable < 10:
        print("🧠 Final reasoning wait...")
        time.sleep(5)
        
        # Get final response and yield if there's new content
        final_response = get_full_response() or ""
        if len(final_response) > len(previous_response):
            final_chunk = final_response[len(previous_response):]
            
            chunk_info = {
                'chunk': final_chunk,
                'raw_chunk': final_chunk,
                'chunk_size': len(final_chunk),
                'raw_size': len(final_chunk),
                'total_size': len(final_response),
                'growth_from_start': len(final_response) - baseline_length,
                'timestamp': time.time() - start_time,
                'is_final': True,
                'is_filtered_out': len(final_chunk.strip()) == 0
            }
            yield chunk_info

def filter_chunk_content(chunk):
    """Filter chunk content to remove UI elements"""
    lines = chunk.split('\n')
    filtered_lines = []
    
    for line in lines:
        line = line.strip()
        if (len(line) > 0 and 
            not line in ['How can Grok help?', 'DeepSearch', 'Think', 'Send', 'Upload', 'Grok 3', 'Upgrade to SuperGrok', 'Think Harder'] and
            not re.match(r'^\d+[smh]$', line) and
            not line.isdigit() and
            not line in ['Copy', 'Wrap', 'Collapse']):
            filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)

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
        
        # Remove the line limit to prevent truncation
        for line in lines:
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
    
    # Get baseline BEFORE sending message
    print("\n📊 Getting baseline before sending message...")
    baseline_response = get_full_response() or ""
    baseline_length = len(baseline_response)
    print(f"📊 Baseline response length: {baseline_length}")
    
    # Send the message using CDP
    if send_message_to_grok_cdp(question):
        print("\n🔄 Starting chunk streaming...")
        print("=" * 50)
        
        # Stream chunks using generator with baseline
        total_chunks = 0
        total_chars = 0
        
        for chunk_info in stream_grok_chunks_with_baseline(baseline_response, 180):
            total_chunks += 1
            total_chars += chunk_info['chunk_size']
            
            chunk_type = "FIRST" if chunk_info.get('is_first') else "FINAL" if chunk_info.get('is_final') else "INCREMENTAL"
            filtered_out = " [FILTERED OUT]" if chunk_info.get('is_filtered_out') else ""
            print(f"📦 Chunk #{total_chunks} [{chunk_type}]{filtered_out} ({chunk_info['chunk_size']} chars filtered, {chunk_info['raw_size']} raw, {chunk_info['timestamp']:.1f}s):")
            print("─" * 60)
            if chunk_info.get('is_filtered_out'):
                print("[This chunk was mostly UI elements - showing raw content:]")
                print(chunk_info['raw_chunk'][:300] + ("..." if len(chunk_info['raw_chunk']) > 300 else ""))
            else:
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
